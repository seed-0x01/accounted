#!/usr/bin/env python3
"""Fixture tests for accounted — all pure, no network, no live files required."""
import sys
sys.path.insert(0, "/opt/data/projects/accounted")
import build as A

passed = failed = 0


def check(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print("PASS", name)
    else:
        failed += 1
        print("FAIL", name)


# 1. approximate timestamp parsing
check("approx_time x", A.approx_time("2026-11-16", " 12:2x UTC — run") == "2026-11-16 12:20")
check("approx_time plain", A.approx_time("2026-11-18", " 03:00 UTC") == "2026-11-18 03:00")
check("approx_time none", A.approx_time("2026-11-16", " — genesis") == "2026-11-16 00:00")

# 2. section parsing + ordering
sections = A.parse_sections(
    "# top\nintro\n## 2026-11-18 03:00 UTC — later\nbody two\n"
    "## 2026-11-17 12:2x UTC — earlier\nbody one\n"
)
check("sections count", len(sections) == 2)
check("sections sorted", [s["key"] for s in sections] ==
      ["2026-11-17 12:20", "2026-11-18 03:00"])
check("sections body", "body one" in sections[0]["body"])

# 3. slug extraction + word-boundary pointer detection
slugs = A.slugs_from_projects(
    "- **routecheck.units** — x\n- **uncounted** — y\n- **ab** — too short\n")
check("slug extraction", slugs == ["routecheck", "uncounted"])
check("pointer hit", A.artifacts_in("shipped uncounted today", slugs) == ["uncounted"])
check("word boundary", A.artifacts_in("a routecheckish thing", slugs) == [])

# 4. run -> most recent preceding section
rows = [
    {"date": "2026-11-17", "ts": "2026-11-17T13:00:00Z", "tokens": 100,
     "error": False, "job": "a"},
    {"date": "2026-11-18", "ts": "2026-11-18T04:00:00Z", "tokens": 300,
     "error": True, "job": "b"},
    {"date": "2026-11-16", "ts": "2026-11-16T01:00:00Z", "tokens": 600,
     "error": False, "job": "c"},
]
title, hits = A.map_run(rows[0], sections, slugs)
check("map_run preceding", title == "2026-11-17 12:2x UTC — earlier" and hits == [])
title2, hits2 = A.map_run(rows[1], sections, slugs)
check("map_run hit", "later" in title2)

# make the earlier section name an artifact
sections[0]["body"] = "shipped uncounted here"
ctx = A.summarize(rows, sections, slugs)
# row a(100)->earlier->accounted; row b(300)->later->burn; row c(600)->before journal->burn
check("coverage 10pct", ctx["coverage"] == 10.0)
check("acc tokens", ctx["acc_tokens"] == 100)
check("bad tokens", ctx["bad_tokens"] == 900)
check("acc runs", ctx["acc_runs"] == 1)
check("total deaths", ctx["total_deaths"] == 1)
check("worst day", ctx["worst"]["date"] == "2026-11-16")
check("burn runs count", len(ctx["burn_runs"]) == 2)

# 5. empty audit never crashes and renders zero
empty = A.summarize([], sections, slugs)
check("empty coverage", empty["coverage"] == 0.0)
check("empty render", "0.0" in A.render(empty) and "class='warn'" not in A.render(empty))

# 6. render carries figures, disclosure, verified verdict text
html = A.render(ctx)
check("render figures", "100" in html and "900" in html and "10.0" in html)
check("render disclosure", "autonomous AI agent" in html)
check("render burn section", "cannot point" in html)
check("no broken format", "%(" not in html)

print("\n%d/%d PASS" % (passed, passed + failed))
sys.exit(0 if failed == 0 else 1)
