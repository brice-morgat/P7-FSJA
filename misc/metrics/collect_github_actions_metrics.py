#!/usr/bin/env python3
import json
import os
import statistics
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso8601(s: str) -> datetime:
    # GitHub returns ISO 8601 like "2026-05-11T12:34:56Z"
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def _fmt_duration(seconds: float) -> str:
    if seconds < 0:
        return "n/a"
    minutes = seconds / 60.0
    if minutes < 1:
        return f"{seconds:.0f}s"
    if minutes < 120:
        return f"{minutes:.1f}min"
    hours = minutes / 60.0
    return f"{hours:.2f}h"


def _percent(n: int, d: int) -> str:
    if d <= 0:
        return "n/a"
    return f"{(100.0 * n / d):.1f}%"


def _median(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return statistics.median(values)


def _p95(values: List[float]) -> Optional[float]:
    if not values:
        return None
    values_sorted = sorted(values)
    idx = int(round(0.95 * (len(values_sorted) - 1)))
    return values_sorted[idx]


def _shell(cmd: List[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def _infer_repo_full_name() -> Optional[str]:
    try:
        url = _shell(["git", "remote", "get-url", "origin"])
    except Exception:
        return None

    # Supports https://github.com/owner/repo(.git) and git@github.com:owner/repo(.git)
    if url.startswith("https://github.com/"):
        path = url.removeprefix("https://github.com/").removesuffix(".git")
        return path
    if url.startswith("git@github.com:"):
        path = url.removeprefix("git@github.com:").removesuffix(".git")
        return path
    return None


class GitHubClient:
    def __init__(self, token: Optional[str]):
        self._token = token

    def _request(self, url: str) -> Any:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "P7-FSJA-metrics-script",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub API error {e.code} for {url}: {body}") from e

    def list_workflow_runs(
        self,
        repo_full_name: str,
        workflow_file: str,
        created_since: datetime,
        per_page: int = 50,
    ) -> List[Dict[str, Any]]:
        since = created_since.strftime("%Y-%m-%dT%H:%M:%SZ")
        url = (
            f"https://api.github.com/repos/{repo_full_name}/actions/workflows/{workflow_file}/runs"
            f"?per_page={per_page}&created=>={since}"
        )
        payload = self._request(url)
        return payload.get("workflow_runs", [])

    def get_run_jobs(self, repo_full_name: str, run_id: int) -> List[Dict[str, Any]]:
        url = f"https://api.github.com/repos/{repo_full_name}/actions/runs/{run_id}/jobs?per_page=100"
        payload = self._request(url)
        return payload.get("jobs", [])

    def get_commit(self, repo_full_name: str, sha: str) -> Dict[str, Any]:
        url = f"https://api.github.com/repos/{repo_full_name}/commits/{sha}"
        return self._request(url)


def _run_duration_seconds(run: Dict[str, Any]) -> Optional[float]:
    started = run.get("run_started_at") or run.get("created_at")
    ended = run.get("updated_at")
    if not started or not ended:
        return None
    return (_parse_iso8601(ended) - _parse_iso8601(started)).total_seconds()


def _job_durations_seconds(jobs: List[Dict[str, Any]]) -> Dict[str, float]:
    durations: Dict[str, float] = {}
    for job in jobs:
        name = job.get("name") or f"job-{job.get('id')}"
        started = job.get("started_at")
        ended = job.get("completed_at")
        if started and ended:
            durations[name] = (_parse_iso8601(ended) - _parse_iso8601(started)).total_seconds()
    return durations


def _extract_commit_timestamp(commit_payload: Dict[str, Any]) -> Optional[datetime]:
    # Prefer commit.author.date; fall back to committer date.
    commit = commit_payload.get("commit", {})
    author = (commit.get("author") or {}).get("date")
    committer = (commit.get("committer") or {}).get("date")
    ts = author or committer
    return _parse_iso8601(ts) if ts else None


@dataclass(frozen=True)
class DoraMetrics:
    deployment_frequency_30d: int
    lead_time_median_seconds: Optional[float]
    change_failure_rate_failures: int
    change_failure_rate_total: int
    mttr_median_seconds: Optional[float]


def _compute_dora(
    gh: GitHubClient,
    repo: str,
    cd_runs: List[Dict[str, Any]],
) -> DoraMetrics:
    successful_deploys = [r for r in cd_runs if r.get("conclusion") == "success"]
    deployment_frequency_30d = len(successful_deploys)

    # Lead time (proxy): commit timestamp -> successful deployment completion timestamp.
    lead_times: List[float] = []
    for run in successful_deploys:
        head_sha = run.get("head_sha")
        completed_at = run.get("updated_at")
        if not head_sha or not completed_at:
            continue
        try:
            commit = gh.get_commit(repo, head_sha)
        except Exception:
            continue
        commit_ts = _extract_commit_timestamp(commit)
        if not commit_ts:
            continue
        lead_times.append((_parse_iso8601(completed_at) - commit_ts).total_seconds())

    lead_time_median_seconds = _median(lead_times)

    # Change failure rate (proxy): failed CD workflow runs / total CD workflow runs.
    failures = len([r for r in cd_runs if r.get("conclusion") not in (None, "success")])
    total = len([r for r in cd_runs if r.get("conclusion") is not None])

    # MTTR (proxy): time from a failed deployment run end -> next successful deployment run end.
    mttr_seconds: List[float] = []
    cd_runs_sorted = sorted(
        [r for r in cd_runs if r.get("updated_at") and r.get("conclusion")],
        key=lambda r: _parse_iso8601(r["updated_at"]),
    )
    success_times = [(_parse_iso8601(r["updated_at"]), r) for r in cd_runs_sorted if r.get("conclusion") == "success"]
    success_times_sorted = sorted(success_times, key=lambda t: t[0])
    for run in cd_runs_sorted:
        if run.get("conclusion") != "failure":
            continue
        failed_end = _parse_iso8601(run["updated_at"])
        next_success = next((t for (t, _) in success_times_sorted if t > failed_end), None)
        if next_success:
            mttr_seconds.append((next_success - failed_end).total_seconds())

    mttr_median_seconds = _median(mttr_seconds)

    return DoraMetrics(
        deployment_frequency_30d=deployment_frequency_30d,
        lead_time_median_seconds=lead_time_median_seconds,
        change_failure_rate_failures=failures,
        change_failure_rate_total=total,
        mttr_median_seconds=mttr_median_seconds,
    )


def _parse_local_json_logs(paths: List[str]) -> Tuple[int, int, int]:
    info = warn = error = 0
    for path in paths:
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                level = (obj.get("level") or obj.get("log", {}).get("level") or "").upper()
                if level == "INFO":
                    info += 1
                elif level == "WARN" or level == "WARNING":
                    warn += 1
                elif level == "ERROR":
                    error += 1
    return info, warn, error


def _md_table(headers: List[str], rows: List[List[str]]) -> str:
    out = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def main(argv: List[str]) -> int:
    repo = os.environ.get("GITHUB_REPO") or _infer_repo_full_name()
    if not repo:
        print("Erreur: impossible de determiner le repo GitHub. Definis GITHUB_REPO=owner/repo.", file=sys.stderr)
        return 2

    token = os.environ.get("GITHUB_TOKEN")
    gh = GitHubClient(token=token)

    now = _utc_now()
    since_30d = now - timedelta(days=30)

    try:
        ci_runs = gh.list_workflow_runs(repo, "ci.yml", created_since=since_30d, per_page=50)
        cd_runs = gh.list_workflow_runs(repo, "cd.yml", created_since=since_30d, per_page=50)
    except Exception as e:
        print(f"Erreur API GitHub: {e}", file=sys.stderr)
        print("Astuce: exporte un token avec droits lecture Actions, ex: GITHUB_TOKEN=ghp_xxx", file=sys.stderr)
        return 2

    dora = _compute_dora(gh, repo, cd_runs)

    # CI durations (pipeline performance)
    ci_durations: List[float] = []
    for r in ci_runs:
        if r.get("conclusion") is None:
            continue
        d = _run_duration_seconds(r)
        if d is not None:
            ci_durations.append(d)
    ci_success = len([r for r in ci_runs if r.get("conclusion") == "success"])
    ci_total = len([r for r in ci_runs if r.get("conclusion") is not None])

    # CD durations
    cd_durations: List[float] = []
    for r in cd_runs:
        if r.get("conclusion") is None:
            continue
        d = _run_duration_seconds(r)
        if d is not None:
            cd_durations.append(d)
    cd_success = len([r for r in cd_runs if r.get("conclusion") == "success"])
    cd_total = len([r for r in cd_runs if r.get("conclusion") is not None])

    local_info, local_warn, local_error = _parse_local_json_logs(
        ["logs/backend/backend.log", "logs/frontend/frontend.log"]
    )

    print(f"# Tableau provisoire - DORA & KPI (sur 30 jours)\n")
    print(f"- Repo: `{repo}`")
    print(f"- Periode: `{since_30d.strftime('%Y-%m-%d')}` -> `{now.strftime('%Y-%m-%d')}` (UTC)\n")

    dora_rows = [
        [
            "Deployment frequency",
            f"{dora.deployment_frequency_30d} deploy(s) / 30j",
            "Nb de runs `cd.yml` en succes sur 30 jours (proxy du nombre de deploiements).",
        ],
        [
            "Lead time for changes",
            _fmt_duration(dora.lead_time_median_seconds) if dora.lead_time_median_seconds else "n/a",
            "Mediane (commit timestamp -> fin du run `cd.yml` en succes) (proxy).",
        ],
        [
            "Change failure rate",
            _percent(dora.change_failure_rate_failures, dora.change_failure_rate_total),
            "Runs `cd.yml` en echec / total runs `cd.yml` (proxy, ne capture pas tous les incidents prod).",
        ],
        [
            "MTTR",
            _fmt_duration(dora.mttr_median_seconds) if dora.mttr_median_seconds else "n/a",
            "Mediane (fin run `cd.yml` en echec -> fin run `cd.yml` suivant en succes) (proxy).",
        ],
    ]
    print(_md_table(["Metrie DORA", "Valeur", "Methode de calcul"], dora_rows))
    print()

    kpi_rows = [
        [
            "Taux de succes CI",
            _percent(ci_success, ci_total),
            "Runs `ci.yml` en succes / total runs `ci.yml` sur 30 jours.",
        ],
        [
            "Temps CI (p50)",
            _fmt_duration(_median(ci_durations)) if _median(ci_durations) else "n/a",
            "Duree du workflow `ci.yml` (run_started_at -> updated_at).",
        ],
        [
            "Temps CI (p95)",
            _fmt_duration(_p95(ci_durations)) if _p95(ci_durations) else "n/a",
            "95e percentile duree workflow `ci.yml`.",
        ],
        [
            "Taux de succes CD",
            _percent(cd_success, cd_total),
            "Runs `cd.yml` en succes / total runs `cd.yml` sur 30 jours.",
        ],
        [
            "Temps CD (p50)",
            _fmt_duration(_median(cd_durations)) if _median(cd_durations) else "n/a",
            "Duree du workflow `cd.yml` (run_started_at -> updated_at).",
        ],
    ]
    print(_md_table(["KPI operationnel", "Valeur", "Methode de calcul"], kpi_rows))
    print()

    print("## Indicateurs applicatifs (extrait local de logs)\n")
    print(
        _md_table(
            ["KPI", "Valeur", "Note"],
            [
                ["Nb logs INFO", str(local_info), "Comptage simple sur `logs/*/*.log` (JSON lines)."],
                ["Nb logs WARN", str(local_warn), "A relier a un seuil (ex: > X/h)."],
                ["Nb logs ERROR", str(local_error), "A relier a la fiabilite (ex: erreurs/req)."],
            ],
        )
    )
    print()

    print("## Commentaires / limites\n")
    print("- Les calculs DORA ci-dessus sont des *proxies* basees sur GitHub Actions; idealement, relier aux evenements prod (incidents, rollback, erreurs ELK post-deploy).")
    print("- Pour fiabilite, privilegier Kibana (taux d'erreurs, pics) plutot que les 2 fichiers `logs/*/*.log`.")
    print("- Assure-toi d'avoir au moins 3 executions (CI et CD) sur la periode pour que p50/p95 soient significatifs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
