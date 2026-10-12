# Packaging and Distributing Xdrop for Each Host

Research notes on how Adobe and Blackmagic actually package, sign, install, and retire
extensions — and what that means for shipping Xdrop so it works on a user's machine with
as little ceremony as possible.

**Date of research:** 2026-10-09. Extractor and platform details change; re-check the
Adobe CEP sunset dates and the UXP availability of After Effects before acting on the
migration plan.

---

## 1. Short version

| Host | Mechanism Xdrop uses today | Official package format | Needs signing? | Needs admin? |
| --- | --- | --- | --- | --- |
| DaVinci Resolve | Utility **script** (`Xdrop.py`) | none — plain file in a `Scripts/` folder | no | **no**, if installed per-user |
| DaVinci Resolve (Studio only) | not used | Workflow Integration plugin folder | no | yes (shared folder) |
| Premiere Pro | **CEP** panel (folder copy) | `.zxp` (CEP) / `.ccx` (UXP) | `.zxp`: yes, always / `.ccx`: no | no for per-user CEP, no for `.ccx` |
| After Effects | **CEP** panel (folder copy) | `.zxp` (CEP) / `.ccx` (UXP, beta) | as above | as above |

The two structural takeaways:

1. **CEP is on a published countdown.** Adobe has committed to removing it from new
   versions of the flagship apps starting **December 2029**. Premiere Pro already stops
   accepting new CEP submissions to the Adobe Marketplace in **December 2027**. Xdrop's
   Adobe integration is CEP, so this is a scheduled migration, not a hypothetical.
2. **Resolve's install does not require administrator rights if done per-user**, but
   Xdrop currently writes to the all-users location, which usually does.

---

## 2. Adobe CEP (what Xdrop's Adobe panel is)

CEP = Common Extensibility Platform. An extension is a folder containing `CSXS/manifest.xml`
plus HTML/JS, and optionally a `jsx/` ExtendScript host script — exactly the layout in
[apps/premiere-plugin](../apps/premiere-plugin).

### 2.1 Packaging into `.zxp`

Adobe's tool is **ZXPSignCmd** (from the [CEP Resources repo](https://github.com/Adobe-CEP/CEP-Resources)).
A `.zxp` is a ZIP plus a signature; the signature is what makes it installable.

Create a certificate (self-signed is enough for sideloading):

```bash
ZXPSignCmd -selfSignedCert <countryCode> <stateOrProvince> <organization> \
           <commonName> <password> <outputPath.p12>
```

Package and sign, **always with a timestamp**:

```bash
ZXPSignCmd -sign <inputDir> <outputZxp> <p12> <p12Password> -tsa <timestampURL>
# e.g. -tsa http://time.certum.pl/  or  http://timestamp.comodoca.com/rfc3161
```

Verify (this checks the signature, **not** the content of the extension):

```bash
ZXPSignCmd -verify <zxp> -certinfo
```

### 2.2 The certificate-expiry trap

From Adobe's own packaging guide, the validation outcomes are:

| Signature state | Result |
| --- | --- |
| No signature | Extension does not run |
| Invalid signature | Extension does not run |
| Certificate expired, **no timestamp** | Extension does not run |
| Certificate expired, **valid timestamp** | Extension runs normally |
| Valid signature | Extension runs normally |

Two consequences that bite shipped products:

- **A `.zxp` can stop working for every user, unprompted, on a date.** Certificates are
  typically valid one to four years, and CEP re-checks the certificate *every time a host
  loads the extension* — not just at install. Without a timestamp, expiry is fatal, with
  no warning beforehand.
- **Repackaging is required** before the certificate expires, and users must reinstall.
  A timestamp extends the validity of the signature, which is why `-tsa` is not optional
  in practice.

### 2.3 Installing a `.zxp`

| Method | Notes |
| --- | --- |
| Creative Cloud / Adobe Exchange | The normal consumer path; extension appears in the Marketplace and installs via CC Desktop |
| `ExManCmd --install <zxpPath>` | Adobe's command-line Extension Manager; the links Adobe documents are legacy |
| Anastasiy's Extension Manager | Popular third-party `.zxp` installer |
| Managed enterprise package | Bundle into a CC deployment package |

### 2.4 Installing without a `.zxp` (what Xdrop does)

Copy the folder into the CEP extensions directory and enable debug mode:

- Windows: `%APPDATA%\Adobe\CEP\extensions\<extension-id>`
- macOS: `~/Library/Application Support/Adobe/CEP/extensions/<extension-id>`

**Unsigned (directory) installs require `PlayerDebugMode`:**

- Windows: `HKCU\Software\Adobe\CSXS.<n>` → `PlayerDebugMode` = `"1"` (`REG_SZ`), for each
  CSXS major version the hosts use
- macOS: `defaults write com.adobe.CSXS.<n> PlayerDebugMode 1`

Signed extensions installed through CC do **not** need `PlayerDebugMode`.

### 2.5 Observable 2026 risk on Premiere Pro

Adobe's official timeline says Premiere Pro moves to CEP-disabled-by-default in
**December 2028**, and that users can re-enable it. Real-world reports are ahead of that
schedule:

- [AutoSubs #571 (Jun 2026)](https://github.com/tmoroney/auto-subs/issues/571) — a CEP
  extension simply absent from `Window > Extensions` in Premiere Pro 2026, and manual
  copying to the CEP folder did not help; the maintainer's fix touched CEP *loading*.
- [Adobe community thread (Mar 2026)](https://community.adobe.com/questions-729/i-can-t-get-cep-extensions-or-uxp-to-work-within-premiere-1552300) —
  CEP extension in the correct macOS folder with `PlayerDebugMode = 1` set for CSXS 11–13
  and a correct `PPRO` manifest, still not listed.

**Honest read:** I could not pin the exact cause to a single documented toggle in either
report. Both are consistent with Premiere Pro 2026 tightening CEP loading beyond what the
published timeline implies. Treat "CEP works on Premiere Pro 2026" as **unverified** and
test it against a real 26.x install before shipping; do not rely on the 2028 date alone.
Note that **ExtendScript is explicitly not part of this transition**, so host-side `.jsx`
logic is not on the clock.

---

## 3. Adobe UXP (the successor to CEP)

UXP = Unified Extensibility Platform. Packaged as **`.ccx`**, documented for Premiere Pro
at [developer.adobe.com/premiere-pro/uxp](https://developer.adobe.com/premiere-pro/uxp/plugins/distribution/package/).

### 3.1 What is genuinely easier than CEP

- A `.ccx` is **a plain ZIP**.
- **No digital signature and no timestamp are required** — this removes the entire
  certificate-expiry failure mode described in §2.2.
- **Creative Cloud Desktop installs it directly**, which Adobe describes as more reliable
  and less error-prone than `ExManCmd`. Users double-click a file; that is the whole
  install.
- No MXI packaging configuration files.

### 3.2 Constraints that shape how you package

- **`manifest.json` needs a unique `id`.** For Marketplace listing, the ID must come from
  the Developer Distribution portal and must match the portal exactly or validation fails.
- **Use a different ID for non-Marketplace distribution.** CC Desktop validates a plugin's
  ID against the user's Adobe ID entitlements when the plugin is also listed in the
  Marketplace. If you distribute the *same* ID outside the Marketplace, installation can be
  **rejected** because no Marketplace purchase exists. A separate direct-distribution ID
  sidesteps the entitlement check entirely. This matters for Xdrop if it is ever both on
  the Marketplace and self-distributed.
- **One host application per production package.** `host` must be a single object
  (`{ "app": "premierepro", "minVersion": "25.6.0" }`). The array form is development-only.
  So Premiere Pro and After Effects need **separate `.ccx` files** — unlike the single
  shared CEP panel Xdrop ships today.
- **Hybrid plugins** (native C++ `.uxpaddon` alongside JS) additionally require: per-OS/arch
  folders (`mac/arm64`, `mac/x64`, `win/x64`), Apple Developer ID **signing and
  notarization** (self-signed not accepted, cert valid ≥ 1 year), all three architectures
  for Marketplace acceptance, and **OS administrator credentials at install time**. Avoid
  native code if a pure-JS plugin can do the job.
- UXP is a **different security and API model**; Adobe states that migrations "may require
  adopting UXP-supported patterns rather than a 1:1 port", and points at **Webview** and
  **Hybrid** plugins for architectures that do not map directly. Whether the existing
  `jsx/hostscript.jsx` functions can be reused from a UXP plugin at all is **not established
  here** and needs checking against the migration guide before planning the port: plan on
  re-implementing the import logic against UXP APIs, and treat any reuse as a bonus.

### 3.3 Availability and the published timeline

From Adobe's September 2026 announcement
([blog.developer.adobe.com](https://blog.developer.adobe.com/en/publish/2026/09/investing-in-the-future-of-creative-cloud-extensibility-uxp-comes-to-our-flagship-applications)):

| App | UXP status | CEP: no new Marketplace submissions | CEP disabled by default |
| --- | --- | --- | --- |
| Premiere Pro | **GA** (Hybrid plugins since 26.2) | Dec 2027 | Dec 2028 |
| After Effects | **Public beta by Nov 2026** | Dec 2028 | Dec 2028 |
| Media Encoder | Public beta | Dec 2028 | Dec 2028 |
| Photoshop | GA since 2020 | Mar 2027 | Dec 2027 |
| InDesign | GA since 2023 | Jan 2028 | Dec 2028 |
| Illustrator | Public beta by Spring 2027 | Dec 2028 | Dec 2028 |

- Every flagship app gets **at least two years** from its UXP public beta before CEP is
  removed from that app.
- **Starting December 2029, CEP is no longer included** in these apps — this is the hard
  end date.
- Existing Marketplace CEP plugins keep working and can still be updated until then.
- CEP plugins distributed **outside** the Marketplace are not affected by Marketplace
  submission cutoffs.
- **ExtendScripts are not affected.**

---

## 4. DaVinci Resolve

Resolve has **three different extension mechanisms**, and they are not interchangeable.

### 4.1 Scripts — what Xdrop uses (works on free and Studio)

A script is just a `.py` or `.lua` file dropped into a `Scripts/<Category>` folder. Resolve
scans on startup and lists it under **Workspace → Scripts**. Category folders determine
where it appears: `Utility` (all pages), `Comp`/`Tool` (Fusion page), or `Edit`/`Color`/
`Deliver`.

| OS | All users (needs admin) | Specific user (no admin) |
| --- | --- | --- |
| Windows | `%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Fusion\Scripts` | `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts` |
| macOS | `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts` | `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts` |
| Linux | `/opt/resolve/Fusion/Scripts` (or `/home/resolve/...`) | `$HOME/.local/share/DaVinciResolve/Fusion/Scripts` |

Advantages for distribution: **no package format, no signing, no installer, no admin
rights** (per-user), and it works on the **free** version as well as Studio. This is by far
the lowest-friction path for Resolve, and it is the right one for Xdrop.

Scripts invoked from the Workflow Integrations area additionally receive `resolve` and
`project` variables injected automatically, and scripting access permission can be
restricted in Resolve Preferences (Console only / local network / all) — relevant to
security guidance, not packaging.

### 4.2 Workflow Integration plugins — a real docked panel (Studio only)

Introduced in Resolve 17/18, these appear under **Workspace → Workflow Integrations**.
A plugin is an **Electron app** with this structure, scanned from the Workflow Integration
Plugins root on startup:

```
com.<company>.<plugin_name>/
├── manifest.xml
├── package.js
├── main.js
├── index.html
├── node_modules/          # Node.js modules
├── js/  css/  img/
└── WorkflowIntegration.node
```

It talks to Resolve through the `WorkflowIntegration` Node module:
`Initialize(pluginId)` → `GetResolve()` → use the usual Resolve API objects. Callbacks are
limited to `RenderStart` / `RenderStop`, and there is **no console-based JavaScript
support**. Timelines are set with `SetAPITimeout(seconds)` (default: no timeout).

**Two hard constraints:**

- **Studio only.** Workflow Integration plugins do not load in the free version of Resolve.
  Widely confirmed by vendors and Blackmagic forum staff.
- **Windows and macOS only** (no Linux). Workflow Integration *scripts* do run on Linux.

So this is the better UX (a docked panel) but it excludes free-version users — which is
most of Xdrop's potential Resolve audience.

### 4.3 `.drfx` — not for this

`.drfx` is a DaVinci Resolve **Fusion template/macro** bundle (effects, transitions, titles,
Generators) that installs into the Effects library. It cannot ship a panel or an
application. It is a common source of confusion, not a packaging option for Xdrop.

### 4.4 Framework versions (Windows)

Blackmagic's README lists Lua 5.1, Python 2.7 64-bit, and Python 3.6 64-bit as scripting
prerequisites ("for all users"), and states that the `RESOLVE_SCRIPT_API` /
`RESOLVE_SCRIPT_LIB` / `PYTHONPATH` environment variables are needed when invoking a script
from an *external* folder. A script inside the `Scripts/` tree is launched from the Resolve
menu instead, so it should not need those variables set by the user.

**Uncertain and worth testing:** the README does not state which interpreter Resolve uses
to run a menu-invoked Python script, and it does not promise that the user's system Python
is what executes it. Treat "`Xdrop.py` runs under the user's own Python" as an assumption
to verify on each platform rather than a documented guarantee.

---

## 5. What this means for Xdrop

Ranked by user-visible benefit per unit of work.

### 5.1 Install Resolve's script per-user, not system-wide — **do this first**

Today [xdrop/resolve/installer.py](../apps/desktop-service/xdrop/resolve/installer.py)
targets only the all-users `Fusion/Scripts/Utility`, which on Windows is
`C:\ProgramData\...` and normally needs elevation. `docs/INSTALLATION.md` already admits
this. Switching to (or falling back to) the per-user path removes the admin prompt
entirely and is the single cheapest reliability win:

- Windows `%APPDATA%\...\Support\Fusion\Scripts\Utility`
- macOS `~/Library/Application Support/.../Fusion/Scripts/Utility`
- Linux `$HOME/.local/share/DaVinciResolve/Fusion/Scripts/Utility`

Try per-user first; keep the all-users path as an opt-in for shared machines.

*Feasible to verify here:* yes — path selection is pure logic and testable; a real
"appears in the Resolve menu" check needs a Resolve install.

### 5.2 Keep the CEP panel, but plan the UXP migration now

- The CEP panel remains usable for years (removal Dec 2029; Premiere disabled-by-default
  Dec 2028), so there is no emergency.
- But **After Effects gets UXP public beta around November 2026** — effectively now — so a
  UXP implementation is the way to be present on AE going forward.
- The CEP panel's `jsx/hostscript.jsx` ExtendScript functions remain usable because
  ExtendScript is explicitly not part of the transition. A UXP plugin would not call them
  the same way, so budget for re-implementing the import logic against UXP APIs.
- Plan for **two `.ccx` packages** (Premiere Pro and After Effects), since production
  packages target a single host.
- Reserve a **separate plugin ID for direct distribution** distinct from any Marketplace ID,
  to avoid the entitlement-rejection trap in §3.2.

### 5.3 If you ship a `.zxp`, automate signing with a timestamp

If Xdrop ever distributes the CEP panel as a `.zxp` (rather than today's folder copy), then:
- sign with `-tsa` **always**, or the extension dies on certificate expiry;
- add a build-time reminder to repackage before the certificate expires;
- note that a `.zxp` install does not need `PlayerDebugMode`, whereas the current folder
  copy does — both paths should stay supported since the folder copy is what works today.

A signed `.zxp` also removes the "unsigned extension" prompt and is the only format Adobe
Exchange / managed deployment accepts.

### 5.4 Consider a Resolve Workflow Integration plugin later, as a Studio premium path

It gives a genuinely docked panel, but it is Studio-only and Windows/macOS-only. Reasonable
as an *additional* option for Studio users, never as a replacement for the script, which
covers free users on all three platforms.

### 5.5 Things to test on real hosts before promising "it just works"

Unverifiable in this repository, and therefore the actual risk list:

1. Whether the CEP panel loads on **Premiere Pro 2026 (26.x)** at all — mixed signals in
   §2.5.
2. Whether `PlayerDebugMode` is needed/sufficient on each installed CSXS major version, and
   that the macOS `defaults write` path is exercised too (the current setup only sets the
   Windows registry key).
3. A `.zxp` install end-to-end: sign, verify, install, load, and confirm the timestamp
   reports as valid.
4. A UXP `.ccx` install via Creative Cloud Desktop on both Premiere Pro and After Effects.
5. The per-user Resolve script path actually appearing under **Workspace → Scripts** on
   Windows, macOS, and Linux.

---

## 6. Sources

- Adobe, *Package, Distribute, Install Guide* (CEP) —
  https://github.com/Adobe-CEP/Getting-Started-guides/blob/master/Package%20Distribute%20Install/readme.md
- Adobe, *ZXPSignCmd* / CEP Resources —
  https://github.com/Adobe-CEP/CEP-Resources
- Adobe, *Package a UXP plugin* (Premiere Pro) —
  https://developer.adobe.com/premiere-pro/uxp/plugins/distribution/package/
- Adobe, *Install a UXP plugin* —
  https://developer.adobe.com/premiere-pro/uxp/plugins/distribution/install/
- Adobe, *CEP to UXP: Creative Cloud Plugin Migration Timeline* (Sep 2026) —
  https://blog.developer.adobe.com/en/publish/2026/09/investing-in-the-future-of-creative-cloud-extensibility-uxp-comes-to-our-flagship-applications
- Adobe, *CEP to UXP Technical Migration Guide* —
  https://developer.adobe.com/uxp/migration-center/uxp-for-cep-devs/technical-migration-guide/
- Blackmagic Design, *Workflow Integrations* README (shipped with Resolve) —
  https://resolvedevdoc.readthedocs.io/en/latest/UI_intro.html
- Blackmagic Design, *Scripting API Introduction* (script folder paths) —
  https://resolvedevdoc.readthedocs.io/en/latest/API_intro.html
- Blackmagic forum, *Workflow integrations are a Studio-only feature* —
  https://forum.blackmagicdesign.com/viewtopic.php?f=12&t=191745
- AutoSubs issue #571, *Premiere Pro 2026 — CEP extension not loading* —
  https://github.com/tmoroney/auto-subs/issues/571
- Adobe community, *I can't get CEP extensions (or UXP) to work within Premiere* (Mar 2026) —
  https://community.adobe.com/questions-729/i-can-t-get-cep-extensions-or-uxp-to-work-within-premiere-1552300
