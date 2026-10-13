# 2FAK Resident - Hardware SSH Key Guide

Using the **2FAK Passkey (Resident)** firmware as a hardware-backed SSH key, aimed at
system administrators who live in remote shells. The private key is generated on the
2FAK and never leaves it; every authentication needs a physical touch, so a stolen laptop
or a compromised jump host cannot use your key without the token in hand.

> This is a Passkey (Resident) firmware feature. Standard (non-resident) `ecdsa-sk` keys
> also work on the 2FAK Secure (Non-Resident) firmware, but the **portable / resident**
> keys described below (carry the key on the token, pull it onto any machine) require the
> Resident firmware, because they are discoverable credentials.

## What you get

- **Hardware-held SSH identity.** The private key lives in the 2FAK; `ssh` talks to it over
  the FIDO2 protocol. Nothing to exfiltrate from disk.
- **Touch-to-authorize every connection.** A compromised bastion cannot silently reuse the
  key while you are logged in.
- **Portable across machines.** A *resident* key is stored on the token and can be pulled
  onto any workstation with `ssh-keygen -K` - no key files to copy between machines.
- **Optional PIN (verify-required).** Force the device PIN in addition to touch for
  high-value hosts.
- **Bonus: Git signing.** The same key signs commits and tags.

## Requirements

- **OpenSSH 8.2 or newer** with FIDO/`libfido2` support on every machine you connect *from*.
  Check with `ssh -V`. (Servers you connect *to* only need 8.2+ to understand the
  `sk-ecdsa-sha2-nistp256@openssh.com` key type in `authorized_keys`.)
- A **2FAK Passkey (Resident)** key. The firmware supports **both ES256 (`ecdsa-sk`) and
  Ed25519 (`ed25519-sk`)**; use whichever your workflow prefers. Both have been tested working
  end to end (key generation + authentication) **locally and against Cloudflare**.
- Linux/macOS: `libfido2` present (usually packaged with OpenSSH). Windows: see
  [Windows](#windows--putty).

Quick capability check (also available via the helper: `python 2FAK-ssh-enroll.py check`):

```bash
ssh -V                       # want OpenSSH_8.2 or newer
ssh-keygen -t ecdsa-sk -f /dev/null -C probe 2>&1 | grep -qi "unknown key type" \
  && echo "no -sk support" || echo "sk supported"
```

## 1. Enroll a resident (portable) key

A *resident* key stores the credential on the token itself, so you can reconstruct it on
any machine later. The local `id_ecdsa_sk_*` file is only a handle + public key - the
secret stays on the 2FAK.

```bash
ssh-keygen -t ecdsa-sk -O resident -O application=ssh:prod \
    -C "2fak:prod" -f ~/.ssh/id_ecdsa_sk_prod
# touch the 2FAK when the LED blinks
```

- `-O resident` - store the credential on the device (this is the portable part).
- `-O application=ssh:<label>` - the FIDO "relying party" string; **must start with `ssh:`**.
  Use distinct labels (`ssh:prod`, `ssh:lab`) if you want separate keys on one token.
- Add `-O verify-required` to force the **device PIN** in addition to touch (see
  [PIN tiering](#5-pin-tiering-touch-only-vs-pintouch)).

This produces `~/.ssh/id_ecdsa_sk_prod` (handle) and `~/.ssh/id_ecdsa_sk_prod.pub` (public
key). See [the helper CLI](#helper-cli-2fak-ssh-enroll) to do this and the backup key in
one guided flow.

## 2. Export a resident key onto a new machine

On a fresh admin workstation you do **not** copy key files around - you plug in the token
and pull the resident keys off it:

```bash
cd ~/.ssh
ssh-keygen -K            # writes id_ecdsa_sk_rk* for each resident key on the token
# touch the 2FAK (and enter the PIN if the key was enrolled verify-required)
```

Then reference the downloaded file with `ssh -i` or an `IdentityFile` line. This is the
workflow that makes the Passkey firmware attractive for admins who move between machines.

> Note: `ssh-keygen -K` works for **anyone holding the token** unless the key was enrolled
> with a device PIN - the touch gate does not protect export. Set a PIN (see
> [PIN tiering](#5-pin-tiering-touch-only-vs-pintouch)).

## 3. Install the public key on servers

For a handful of servers, append the `.pub` line to each server's `~/.ssh/authorized_keys`:

```bash
ssh-copy-id -f -i ~/.ssh/id_ecdsa_sk_prod.pub user@server
# or paste the single line from id_ecdsa_sk_prod.pub into authorized_keys by hand
```

The line is of type `sk-ecdsa-sha2-nistp256@openssh.com`. You can harden it with per-key
options - for example restrict the source network and require user verification (PIN):

```
# ~/.ssh/authorized_keys on the server
from="10.0.0.0/8",verify-required sk-ecdsa-sha2-nistp256@openssh.com AAAAInNr... 2fak:prod
```

`verify-required` makes the server reject the key unless it was used with the device PIN;
`from="10.0.0.0/8"` limits which source networks may use it. (Starting from `restrict` and
re-enabling only what you need, e.g. `restrict,pty,from="10.0.0.0/8"`, is a stricter base.)

### Fleet distribution with Ansible

For many servers, push the public key(s) with configuration management rather than by hand.
Distribute **both** the primary and backup public keys:

```yaml
# roles/ssh_hardware_keys/tasks/main.yml
- name: Install 2FAK hardware SSH keys for admins
  ansible.posix.authorized_key:
    user: "{{ admin_user }}"
    state: present
    key: "{{ item }}"
    exclusive: false
  loop:
    - "{{ lookup('file', 'files/id_ecdsa_sk_prod.pub') }}"
    - "{{ lookup('file', 'files/id_ecdsa_sk_prod_backup.pub') }}"
```

Rotating a key is then a one-line change in the vars/files and a playbook run.

## 4. Bastions and jump hosts (ProxyJump)

Admins rarely reach a server directly. Use **`ProxyJump`**, not agent forwarding - auth
happens locally on each hop and the key is never exposed on the intermediate host:

```
# ~/.ssh/config
Host bastion
    HostName bastion.example.net
    User admin
    IdentityFile ~/.ssh/id_ecdsa_sk_prod

Host prod-*
    ProxyJump bastion
    User admin
    IdentityFile ~/.ssh/id_ecdsa_sk_prod
```

```bash
ssh prod-web01     # you will be asked to touch the key for each hop
```

**Avoid `ForwardAgent yes` to untrusted hosts.** With a hardware key, touch-per-use already
limits misuse, but forwarding still exposes the agent socket on the intermediate machine;
`ProxyJump` sidesteps that entirely. If you must forward, scope it per-host and never to a
shared bastion.

## 5. PIN tiering (touch-only vs PIN+touch)

Match the friction to the value of the host:

| Tier | Enrollment | Login requires |
|------|------------|----------------|
| Staging / lab | `-t ecdsa-sk -O resident` | touch |
| Production / privileged | add `-O verify-required` | **device PIN + touch** |

`verify-required` keys carry the requirement inside the credential, so the server can also
insist on it:

```
# authorized_keys on a production host - reject a key used without user verification
verify-required sk-ecdsa-sha2-nistp256@openssh.com AAAAInNr... 2fak:prod
```

Set or change the device PIN with your normal FIDO2 tooling (e.g. the OS security-key
settings, or `fido2-token -S`). Standard CTAP retry limits apply: the key locks for the
session after repeated wrong PINs and blocks after the retry count is exhausted; a device
reset clears it (and destroys the resident keys).

> **Set a PIN even for touch-only tiers.** A resident key enrolled *without* a device PIN
> can be pulled off the token by **anyone physically holding it**, using `ssh-keygen -K` -
> no PIN, no proof of ownership. The touch requirement only gates *use*, not *export*. For
> any key that matters, set a device PIN (and enroll with `-O verify-required` on privileged
> hosts) so a lost or borrowed token cannot have its keys extracted.

## 6. SSH certificate authority (larger fleets)

Per-server `authorized_keys` does not scale to hundreds of hosts. The modern pattern is an
**SSH CA that issues short-lived user certificates**, with the 2FAK as the human root of
trust:

1. The admin authenticates to the CA / access proxy **with the 2FAK** (touch, and PIN on
   privileged roles).
2. The CA issues a **short-lived certificate** (e.g. 8 hours) scoped to the roles the admin
   is allowed to assume.
3. Servers trust the CA's public key (`TrustedUserCAKeys`), not individual admin keys, so
   revocation and audit are central.

This works with self-managed `ssh-keygen` CAs and with access platforms such as Teleport,
Smallstep `step-ca`, or HashiCorp Vault's SSH secrets engine. The 2FAK's role is the
same in all of them: the phishing-resistant, touch-required credential that gates
certificate issuance. Keep the CA signing key offline/HSM-backed; the 2FAK protects the
*human* step, not the CA itself.

## 7. Backup enrollment (do not skip)

The single most important operational rule: **enroll at least two 2FAK keys** and install
both public keys everywhere (authorized_keys, or register both with the CA). A hardware key
can be lost or damaged; without a backup you are one failure away from being locked out of
production.

- Enroll the primary, then enroll a backup with the **backup key inserted** (same
  `application` label, a different output file).
- Store the backup key physically separately (e.g. a safe).
- The [helper CLI](#helper-cli-2fak-ssh-enroll) prompts for the backup step by default.

## Windows / PuTTY

- **OpenSSH for Windows (recommended):** recent builds support `-sk` keys; use the same
  `ssh-keygen` commands from PowerShell. Ensure the OpenSSH version is 8.2+ (`ssh -V`). This
  is the simplest path on Windows.
- **PuTTY:** mainline PuTTY does **not** natively support FIDO `-sk` keys. Options are the
  `putty-cac` fork (adds FIDO2/PIV support), or keep using mainline PuTTY/WinSCP/FileZilla
  with the OpenSSH agent bridged in via `winssh-pageant`. If you only need PuTTY itself,
  prefer Windows OpenSSH instead.
- **USB-A** is convenient on servers, KVM carts, and older admin hardware where USB-C or
  Bluetooth keys are awkward.

If a tool does not detect the key right after you plug it in, start a fresh terminal (or
restart the SSH agent) so it re-scans for the device, then retry.

## Git commit and tag signing (bonus)

The same hardware key signs Git commits - useful for infrastructure-as-code repos:

```bash
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ecdsa_sk_prod.pub
git config --global commit.gpgsign true      # touch the key when committing
```

On GitHub, add the key under **Settings -> SSH and GPG keys** as **both** an authentication
key and a signing key.

## Limitations and honesty notes

- **Not for unattended automation.** A touch-required key cannot drive cron, CI, or Ansible
  runs on its own. Use the 2FAK for **interactive, privileged, human** sessions; keep
  automation on separate service credentials or short-lived certificates. (`no-touch-required`
  exists but defeats the purpose - avoid it.)
- **Both `ecdsa-sk` (ES256) and `ed25519-sk` (Ed25519) work** (tested locally and with
  Cloudflare). Signing for both runs in the MCU; the per-key material is derived on demand from
  the ATECC-rooted master secret and is never stored (the Ed25519 operation itself is software,
  as the ATECC cannot perform Ed25519 - but the key is still hardware-rooted).
- **Self-tested conformance, not FIDO Certified.** See
  `2FAK Resident - FIDO Conformance Readiness.md`.

## Helper CLI: `2FAK-ssh-enroll`

`2FAK-ssh-enroll.py` (in this folder) is a thin, auditable wrapper around `ssh-keygen` that
guides the resident-key workflow and prompts you to enroll a backup key. It stores nothing
itself and does not talk to the device directly.

```bash
python 2FAK-ssh-enroll.py check                          # verify OpenSSH -sk support
python 2FAK-ssh-enroll.py enroll --name prod --verify-required
python 2FAK-ssh-enroll.py enroll --name lab --no-backup
python 2FAK-ssh-enroll.py export --dir ~/.ssh            # pull resident keys onto a new box
```

`enroll` creates a resident `ecdsa-sk` key (`--verify-required` adds the PIN requirement),
then offers to enroll a backup key with the same application label. `export` wraps
`ssh-keygen -K`. Everything it does can be done by hand with the commands earlier in this
guide.
