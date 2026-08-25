# GitHub profile design and maintenance guide

The public README deliberately borrows the supplied inspiration profile's strongest system—terminal-style section names, GitHub-green accents, generated local SVGs, paired radar charts, local number cards, and compact project cards—without copying its content, portrait, projects, or binary messages.

## Design direction

- Identity: network and infrastructure lead who also ships weekend development projects.
- Visual language: GitHub canvas colors, `#39d353` accents, thin borders, monospace interaction details, and restrained animation.
- Content hierarchy: portrait → `whoami` → toolbox → proof graphs → homelab → activity → selected work → career direction → connect.
- Recruiter story: operations depth first, development evidence second, and cloud/automation trajectory throughout.

## Responsive and theme behavior

GitHub profile READMEs cannot ship custom CSS media queries for the whole document. The profile therefore uses native HTML behavior that GitHub reliably supports:

- Every theme-sensitive visual uses `<picture>` with explicit dark and light `<source>` files.
- Radar and project images are inline fixed-width images with GitHub's `max-width: 100%` behavior. They pair on wide screens and wrap to one full-width image on narrow screens.
- No project-card or radar table locks the page into two columns on mobile.
- Full-width graphics use scalable SVG `viewBox` coordinates, so they remain sharp on retina, ultrawide, tablet, and phone displays.
- Wide infrastructure, achievement, and automation diagrams switch to dedicated vertical SVG variants below 600 px so labels remain readable rather than merely shrinking.
- Text remains real Markdown wherever searchability, accessibility, or recruiter scanning matters.
- Every image has descriptive alternative text and a visible text equivalent nearby.

Theme palette:

| Token | Dark | Light |
| --- | --- | --- |
| Canvas | `#0d1117` | `#ffffff` |
| Primary text | `#e6edf3` | `#24292f` |
| Muted text | `#8b949e` | `#57606a` |
| Grid/border | `#30363d` | `#d0d7de` |
| Accent | `#39d353` | `#1a7f37` |

## Repository structure

```text
RahulSinghParmar/
├── .github/workflows/
│   ├── profile-assets.yml       # GitHub data, cards, radars, calendar
│   ├── snake.yml                # contribution snake/output branch
│   └── validate-profile.yml     # pull-request and push quality gate
├── assets/
│   ├── profile-data.json        # last known-good public data snapshot
│   ├── projects.json            # selected project content
│   ├── skills.json              # editable self-assessed radar values
│   ├── portrait-{light,dark}.svg
│   ├── radar-{skills,languages}-{light,dark}.svg
│   ├── card-stats-{light,dark}.svg
│   ├── languages-{light,dark}.svg
│   ├── achievements-{light,dark}.svg
│   ├── achievements-mobile-{light,dark}.svg
│   ├── project-*-{light,dark}.svg
│   ├── infrastructure-banner-{light,dark}.svg
│   ├── infrastructure-banner-mobile-{light,dark}.svg
│   ├── automation-loop-{light,dark}.svg
│   ├── automation-loop-mobile-{light,dark}.svg
│   ├── metrics.isocalendar.svg  # dark/GitHub default name
│   ├── metrics.isocalendar-light.svg
│   └── spotify-connect.svg
├── scripts/
│   ├── build_profile_assets.py
│   ├── generate_isocalendar.py
│   ├── generate_portrait.py
│   ├── validate_profile.py
│   └── requirements.txt
├── docs/
├── README.md
└── .gitignore
```

The original `photo.png`, `photome.png`, and generated `portrait-cutout-source.png` files are ignored. Only the optimized, transparent SVG renderings are intended for the public repository.

## Local generation

Render from the checked-in last known-good data snapshot:

```text
python scripts/build_profile_assets.py
```

Refresh public GitHub data and render everything:

```text
python scripts/build_profile_assets.py --fetch
```

Regenerate the two portrait variants from the private local source:

```text
python scripts/generate_portrait.py portrait-cutout-source.png assets/portrait-light.svg --theme light
python scripts/generate_portrait.py portrait-cutout-source.png assets/portrait-dark.svg --theme dark
```

The generator reconstructs transparency from the isolated local source, emits no background rectangle, and reveals the portrait row by row from top to bottom. The light portrait gives dark hair a subtle warm-graphite lift; the dark portrait lifts deep shadows so hair and beard stay legible.

## Reliability model

| Feature | Source | Failure behavior |
| --- | --- | --- |
| Portrait, radars, numbers, languages, achievements, projects | Repository-hosted SVG | Always available with the README |
| GitHub data refresh | GitHub REST API with built-in token | Three retries, then renders cached snapshot |
| Contribution calendar | Public contribution API | Three retries; existing checked-in calendar remains visible if refresh fails |
| Contribution snake | `output` branch | Existing SVG remains available if a scheduled generation fails |
| Spotify | Local animated fallback | No broken live card before OAuth is restored |
| Typing line, toolbox, social badges, visitor counter | Small hosted SVG requests | Nonessential decoration; core content remains readable if unavailable |

There are no shared GitHub-stats, streak-stats, trophy, activity-card, or top-language rendering services in the critical path.

## Automatic versus curated data

- `card-stats`, `languages`, the right-hand language radar, project metadata, achievements, and the 3D contribution calendar refresh from public GitHub data every 12 hours.
- The contribution snake refreshes daily on its own workflow and is published to the `output` branch.
- The left-hand skill radar is self-assessed. Its SVG refreshes automatically whenever `assets/skills.json` changes, but the labels and percentages are deliberately curated rather than inferred from repository bytes.
- PowerShell appears in the live language radar only when GitHub Linguist detects committed PowerShell files in original, non-archived repositories. The visible toolbox and automation radar can accurately describe professional PowerShell usage even when workplace scripts are private.

## Performance decisions

- Only one portrait variant is selected by `<picture>` for the active theme.
- Core graphs and cards are compact SVG rather than GIF, PNG, or remote rendered screenshots.
- Stats and languages are generated in one scheduled job instead of requesting several public rendering services on every profile view.
- Animation is limited to the portrait row reveal, infrastructure packets, the contribution snake, and one automation pulse.
- Generated data is committed only when content changes; timestamps are excluded to prevent empty scheduled commits.
- The profile avoids large responsive tables, decorative screenshots, hidden duplicate sections, and badge walls.

## Binary interaction

The hero and automation footer contain:

```text
01100001 01110101 01110100 01101111 01101101 01100001 01110100 01100101
```

Split into eight-bit ASCII bytes, it decodes to `automate`. The README includes a collapsible decoder so the detail is discoverable rather than decorative noise. Binary strings work well in technical portfolios when they reinforce a real concept, remain short, and include an accessible explanation.

## Recruiter and ATS guidance

- Keep the exact role title `Team Lead Network Engineer` within the first screen.
- Preserve visible terms for network engineering, infrastructure operations, network security, AWS, data center operations, Windows Server, Active Directory, Linux, VPC, EC2, IAM, monitoring, vulnerability assessment, and Docker.
- Add verified scope metrics when disclosure is allowed: sites supported, devices managed, uptime, incidents resolved, remediation volume, or team size.
- Pin `home-server-heartbeat`, `maintenance-page`, `Portfolio`, and `JAVA-Core` in the same order as the README.
- Add architecture diagrams, screenshots, licenses, setup instructions, and measurable outcomes to each featured repository.
- Link certifications only to issuer-hosted credential pages.

## Mobile QA checklist

Before merge, preview GitHub at approximately 360 px, 768 px, and desktop width in both themes:

- No horizontal scrollbar.
- Complete portrait hairline and readable face.
- Radars wrap rather than shrink into unreadable halves.
- Project cards wrap one per line on phones.
- Text remains readable without zoom.
- Infrastructure and automation labels remain legible.
- Snake and contribution calendar scale without clipping.
- Light assets never show dark rectangles, and dark assets merge with `#0d1117`.

## SEO and discoverability

- Recommended profile bio: `Team Lead Network Engineer | Infrastructure Operations | Network Security | AWS | Weekend Developer`.
- Recommended profile topics: `network-engineering`, `infrastructure`, `network-security`, `aws`, `homelab`, `system-administration`, `devops`, and `automation`.
- Use concise repository descriptions that state the problem and core technology.
- Keep the same professional name, headline, location, and links across GitHub, LinkedIn, the resume, and portfolio.
- Publish practical notes about troubleshooting, homelab reliability, AWS networking, vulnerability management, and automation.

## Legacy cleanup

The obsolete `index.html`, `rahulsinghparmar_files/`, `assets/banner.png`, and `assets/header.png` site-export files were removed from the release candidate after confirming that no README, asset generator, workflow, or documentation page referenced them. They remain recoverable from Git history.
