# INSTALL AND DEPLOY — nt_construction

Status: started 2026-11-02 (server dependencies, language, roles). Completed in Phase 5.

## 1. Server requirements
| Component | Version / note |
|---|---|
| Odoo | 19.0 (Community or Enterprise) |
| Python | 3.12, Odoo's `requirements.txt` |
| PostgreSQL | 14+ |
| **rtlcss** (Node.js) | **Required for Arabic.** Odoo builds the right-to-left stylesheet with it; without it the Arabic UI is not mirrored and the log shows `You need https://rtlcss.com/ to convert css file to right to left compatiblity` |

Install rtlcss (Debian/Ubuntu, as root):
```bash
apt-get install -y nodejs npm
npm install -g rtlcss
rtlcss --version          # must print a version; Odoo looks for `rtlcss` on the PATH of the Odoo service user
```
After installing it on a running server, restart Odoo; RTL assets are regenerated on the next page load.

## 2. Addons path
`custom_addons/` must be on the addons path, after Odoo's own addons:
```ini
addons_path = /opt/odoo/odoo/addons,/opt/odoo/addons,/opt/odoo/custom_addons
```

## 3. Install / upgrade
```bash
./odoo-bin -c odoo.conf -d <db> -i nt_construction --stop-after-init   # first install
./odoo-bin -c odoo.conf -d <db> -u nt_construction --stop-after-init   # upgrade
```
Upgrading from a version before 19.0.1.2.0 removes the old "every internal user" access rights:
users without a construction role lose access until a role is assigned (DECISIONS L15).

## 4. Arabic with Western digits (provisional, DECISIONS S9)
The module ships the language **Arabic (Egypt) / العربية (مصر)** (`ar_EG`), inactive by default:
Arabic text and right-to-left layout, Western digits (0-9) for amounts and dates on screens and PDFs.
1. Settings › Languages › Add Languages › *Arabic (Egypt)* (loads the Arabic translations).
2. Set it on the users (Preferences › Language) instead of *Arabic* (`ar_001`), which shows
   Arabic-Indic digits for dates in the web client.

## 5. Roles
Assign each user one or more construction roles (Settings › Users › *Construction* section):
Tender Engineer, Site Engineer, Quantity Surveyor, Project Manager, Accountant,
Approval: Level 1 or Level 2 / Management. See `DECISIONS.md` Q2 for the access matrix.
