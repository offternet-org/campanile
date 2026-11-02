<p align="right"><b>English</b> · <a href="GESTIONE.md">Italiano</a></p>

# Running a Campanile

## Notices and moderation

The **`/admin.html`** page posts official notices, marks blocked streets for the navigator, and
removes fake, offensive or outdated posts.

It **only works on the Campanile itself**, because on the open Wi-Fi the password would travel in
clear text for anyone nearby to read.

- **Laptop:** open `http://localhost:8080/admin.html` on the laptop. The password is in the black
  window and in `data/admin-password.txt`.
- **Raspberry Pi:** from a computer **by cable**, with SSH on, through an encrypted tunnel,
  `ssh -L 8080:localhost:80 user@<the Raspberry's cable address>`, then open
  `http://localhost:8080/admin.html`. With a desktop on the Raspberry, its own browser works too
  (`http://localhost/admin.html`). The firewall blocks SSH from the hotspot. The password is
  shown at the end of installation and saved in `/etc/campanile/password`.

Each post and registered name gets a **number and a code** (like `K7M2-QX9P`) that lets its
author remove it.

If someone floods the board, the admin page shows new posts **waiting for approval**, and can
close in one click all posts from one device or from the last 15 or 60 minutes.

Posts expire after 14 days, "I'm safe" names after 60 (the `server.py` options `--post-days` and
`--safe-days` change this, 0 keeps them). The admin page also shows a log of what was done, when and
by whom, and the Campanile's clock, which you can set there (without internet a Raspberry restarts
behind).

### The emergency number

The pages tell people to call 112, Europe's number. Elsewhere, write your area's number under
**Emergency number** on the admin page. A laptop set to the United States or Canada starts with
911 by itself.

### More than one volunteer

With the main password, **Who runs this Campanile** gives each volunteer a password of their own.
The Campanile makes it (like `K7M2-QX9P-T2PA-8WNE`) and shows it once: write it down and hand it
over. They can do everything except add or remove people, and the log shows their name. If
someone leaves, remove only them: their password stops working at once.

### Where to put it: the coverage test

Before deciding where a Campanile goes, or a second one, walk around with a phone and measure.
**Coverage test** on the admin page turns it on for 2 hours, then it turns itself off, and shows
its address and a QR code. On a phone on the Campanile's Wi-Fi, open it, write where you are
("3rd floor, landing") and tap **Measure here**. Each measure takes a few seconds: 20 short
messages, the home page opened as a phone opens it, a test post (read and dropped, it never
reaches the board) and a 256 kB download. The answer:

- **Good**: nothing lost, half the replies within 150 ms, the slowest within 0.5 s, at least
  2 Mbit/s;
- **Fair**: at most 1 in 10 lost, half within 0.6 s, at least 0.3 Mbit/s;
- **Bad**: anything less.

Where nothing gets through, the measure waits on the phone and goes by itself, with its time,
once you are back in range: the holes matter most. The admin page lists every measure, refreshed
while the test is on, and **Clear** (tap twice) empties the list. The last 500 are kept. On the
[bench](BENCH.md), where the test said good or fair, two Campaniles swapped their boards in time
469 times out of 470.

### Signed notices (optional)

An authority, such as civil protection, can sign its notices. Only notices signed with its key
show *"Notice signed · Protezione Civile Torino"*.

1. **The authority**, once, on its own computer (`pip install cryptography`):
   `scripts/sign-notice.py keygen --name "Protezione Civile Torino" --out keys/`.
   Keep the private key on that computer only.
2. **Each Campanile**, before the emergency, adds the public part as
   `{"keys": [ ...public.json... ]}` to `/etc/campanile/trusted-keys.json` (Raspberry) or
   `data/trusted-keys.json` (laptop).
3. **For each notice**, run `scripts/sign-notice.py sign --key ... --title ... --text ... --urgent`
   and paste the output in the admin page. Signed notices expire (24 hours by default, 7 days at
   most) and can't be published twice.

The `server.py` option `--require-signed` makes a Campanile refuse unsigned official notices.

### Official alerts in CAP

CAP (Common Alerting Protocol) is the standard format for public warnings, used by IT-alert and
Italian civil protection. Their Italian profiles only add rules to CAP 1.1 and 1.2.

On the admin page, **Load an official alert (CAP)** turns an alert file into a notice. It uses
the admin page's language when the alert has it, turns red if severe or extreme, shows the
issuer's name, and disappears when the alert expires. Tested on the eight messages IT-alert has
published ([pcm-dpc/IT-alert-Hub](https://github.com/pcm-dpc/IT-alert-Hub), all public tests, so
refused as exercises, and read in full once marked as real) and on five real alerts of the Italian
Air Force's weather service.

With a reason each time, the reader refuses any DTD or entity (how XML files attack their
reader), files over 512 kB, exercises, tests, cancellations, alerts not meant for the public,
expired ones and the same alert twice.

**What it doesn't do.** It doesn't check the alert's own digital signature, so the issuer shown is
the one the file names, trusted because the Campanile's admin loaded it. It doesn't receive alerts
by itself.

### Handing over the "I'm safe" names (PFIF)

After an emergency, the names can go to whoever gathers news of missing people. **Export the names
(PFIF)** saves a PFIF 1.4 file, the format Google Person Finder used. Each record says it is not
verified, since anyone can register any name. The codes that remove a name and the phones' tags
never leave. The file holds names, messages and places, so it is personal data, only for those who
need it.
