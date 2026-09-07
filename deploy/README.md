# Déploiement VPS — mytimalove.com

Guide pour installer TimaLove sur un **VPS Ubuntu** (sans Webuzo), avec le domaine géré sur **Cloudflare**.

| Élément | Valeur |
|--------|--------|
| Domaine | `mytimalove.com` |
| VPS (exemple) | `149.56.140.166` |
| Utilisateur app | `jomas` |
| Dépôt | `/home/jomas/timalove` |
| Stack | Django + Daphne + Celery + Redis + PostgreSQL + Nginx |

---

## Scripts

| Fichier | Rôle |
|---------|------|
| [`install-vps.sh`](install-vps.sh) | Installation complète (paquets, DB, Redis, clone, services, Nginx) |
| [`enable-ssl.sh`](enable-ssl.sh) | Certificat Let's Encrypt (Certbot) après DNS |
| [`env.mytimalove.example`](env.mytimalove.example) | Modèle `.env` production |
| [`nginx-vps.conf.template`](nginx-vps.conf.template) | Vhost Nginx (HTTP + WebSocket `/ws/`) |
| [`../timalove/deploy.sh`](../timalove/deploy.sh) | Mises à jour après l’install (`git pull`, migrate, static, restart) |

> L’ancien hébergement Webuzo utilise encore [`bootstrap.sh`](bootstrap.sh). Pour le **nouveau VPS Ubuntu**, utiliser uniquement `install-vps.sh`.

---

## 0. Configurer Git sur le VPS (à faire en premier)

À faire **avant** l’installation, connecté en SSH avec l’utilisateur app (`jomas`).  
Cela identifie correctement les opérations Git sur le serveur et évite les messages « Please tell me who you are » si un commit local est nécessaire.

### Identité Git (obligatoire)

```bash
# Sur le VPS, en tant que jomas (pas root)
git config --global user.name "nick-dev12"
git config --global user.email "webgeniuses12@gmail.com"

# Options utiles
git config --global init.defaultBranch main
git config --global pull.rebase false
git config --global color.ui auto

# Vérifier
git config --global --list
```

Résultat attendu :

```text
user.name=nick-dev12
user.email=webgeniuses12@gmail.com
color.ui=auto
pull.rebase=false
```

Utilisez le même email que sur https://github.com/settings/emails.

### Accès GitHub (si le dépôt devient privé ou pour `git push` depuis le VPS)

Le clone / pull en **HTTPS** sur un dépôt **public** fonctionne sans token.  
Si GitHub demande une authentification :

**Option A — clé SSH (recommandée)**

```bash
ssh-keygen -t ed25519 -C "webgeniuses12@gmail.com" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub
```

1. Copier la clé affichée  
2. GitHub → **Settings → SSH and GPG keys → New SSH key**  
3. Basculer le remote du dépôt (après clone / install) :

```bash
cd /home/jomas/timalove
git remote set-url origin git@github.com:nick-dev12/timalove.git
git remote -v
ssh -T git@github.com
```

**Option B — HTTPS + Personal Access Token**

```bash
# Lors du premier git pull / push : username GitHub + token (pas le mot de passe compte)
git config --global credential.helper store
```

### Où se trouve la config

| Fichier | Portée |
|---------|--------|
| `~/.gitconfig` | Global pour l’utilisateur `jomas` |
| `/home/jomas/timalove/.git/config` | Uniquement ce dépôt (remote, branche…) |

> Important : configurez Git avec **`jomas`**, car `deploy.sh` exécute `git pull` via cet utilisateur.  
> Une config faite uniquement sous `root` (`sudo`) ne s’applique pas aux mises à jour de l’app.

---

## 0b. SSH sans mot de passe (PC → VPS) + sudo sans mot de passe

Pour travailler depuis Windows sans retaper le mot de passe SSH à chaque commande, et pour lancer `sudo` / migrations sans prompt.

### A. Clé SSH sur votre PC (PowerShell)

```powershell
# 1) Créer une clé (une seule fois) — Entrée pour accepter le chemin par défaut
ssh-keygen -t ed25519 -C "webgeniuses12@gmail.com"

# Fichiers créés en général :
#   C:\Users\jomas\.ssh\id_ed25519      (privée — ne jamais partager)
#   C:\Users\jomas\.ssh\id_ed25519.pub  (publique)
```

### B. Copier la clé publique sur le VPS

**Option 1 — automatique (si `ssh` demande encore le mot de passe une fois) :**

```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh jomas@149.56.140.166 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

**Option 2 — manuelle :**

```powershell
# Afficher la clé publique et la copier
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
```

Sur le VPS (session SSH actuelle) :

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
nano ~/.ssh/authorized_keys
# Coller la ligne entière qui commence par ssh-ed25519 ...
chmod 600 ~/.ssh/authorized_keys
```

### C. Tester depuis le PC

```powershell
ssh jomas@149.56.140.166
# ne doit plus demander le mot de passe de connexion
```

Config SSH optionnelle (PC) — fichier `C:\Users\jomas\.ssh\config` :

```text
Host timalove-vps
    HostName 149.56.140.166
    User jomas
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
```

Puis : `ssh timalove-vps`

### D. Sudo sans mot de passe (sur le VPS)

Toujours en SSH, une **dernière fois** avec le mot de passe sudo :

```bash
sudo visudo -f /etc/sudoers.d/jomas-timalove
```

Contenu du fichier (une seule ligne) :

```text
jomas ALL=(ALL) NOPASSWD:ALL
```

Sauvegarder, puis tester :

```bash
sudo -n true && echo "sudo OK sans mot de passe"
```

> Sécurité : n’activez `NOPASSWD` que si vous êtes le seul à avoir la clé SSH privée.  
> Préférez toujours la clé SSH plutôt que de désactiver le mot de passe de connexion SSH.

### E. Copier des fichiers PC → VPS (pour la migration)

```powershell
# Exemple
scp .\tima.dump jomas@149.56.140.166:/tmp/
scp .\timalove-media.tgz jomas@149.56.140.166:/tmp/
```

### F. Accès temporaire par IP (sans domaine)

Tant que Cloudflare pointe encore vers l’ancien site, ouvrez le nouveau VPS via l’IP :

`http://149.56.140.166/`

Sur le VPS :

```bash
ENV=/home/jomas/timalove/timalove/.env
IP=149.56.140.166

# Autoriser l’IP + cookies en HTTP (temporaire)
sudo sed -i "s|^ALLOWED_HOSTS=.*|ALLOWED_HOSTS=mytimalove.com,www.mytimalove.com,${IP},127.0.0.1|" "$ENV"
sudo sed -i "s|^CSRF_TRUSTED_ORIGINS=.*|CSRF_TRUSTED_ORIGINS=http://${IP},https://mytimalove.com,https://www.mytimalove.com|" "$ENV"
sudo sed -i "s|^SITE_URL=.*|SITE_URL=http://${IP}|" "$ENV"
sudo sed -i "s|^SESSION_COOKIE_SECURE=.*|SESSION_COOKIE_SECURE=False|" "$ENV"
sudo sed -i "s|^CSRF_COOKIE_SECURE=.*|CSRF_COOKIE_SECURE=False|" "$ENV"
sudo sed -i "s|^SECURE_SSL_REDIRECT=.*|SECURE_SSL_REDIRECT=False|" "$ENV"

# Nginx : accepter aussi l’IP
sudo sed -i "s/server_name .*/server_name mytimalove.com www.mytimalove.com ${IP};/" /etc/nginx/sites-available/timalove.conf
sudo sed -i 's/listen 80;/listen 80 default_server;/' /etc/nginx/sites-available/timalove.conf
sudo sed -i 's/listen \[::\]:80;/listen [::]:80 default_server;/' /etc/nginx/sites-available/timalove.conf

sudo nginx -t && sudo systemctl reload nginx
sudo systemctl restart daphne-timalove
```

Navigateur : **http://149.56.140.166/**

Quand le DNS + SSL seront prêts, remettez dans `.env` :
`SITE_URL=https://mytimalove.com`, `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, `SECURE_SSL_REDIRECT=True`.

---

## 1. Cloudflare — DNS

Dans le tableau DNS de `mytimalove.com` :

1. **Supprimer** les CNAME Vercel de `@` (`mytimalove.com`) et `www`.
2. **Créer** :
   - Type **A**, Nom `@`, Contenu = IP du VPS, Proxy = **DNS only** (nuage gris)
   - Type **A**, Nom `www`, Contenu = IP du VPS, Proxy = **DNS only**
3. **Ne pas modifier** les enregistrements mail (`mail`, MX SES, SPF, DMARC, etc.) sauf besoin métier.
4. Après SSL réussi (étape 3) :
   - SSL/TLS Cloudflare → mode **Full (strict)**
   - Optionnel : réactiver le proxy orange (Proxied)

Vérification depuis un PC :

```bash
nslookup mytimalove.com
# doit afficher l’IP du VPS (pas vercel-dns)
```

### SMTP / e-mails transactionnels (Namecheap vs VPS)

Le site `mytimalove.com` pointe vers le **nouveau VPS** (`149.56.140.166`), mais la messagerie peut rester sur l’**hébergement mutualisé Namecheap**.

| Hôte | IP actuelle (indicatif) | Rôle |
|---|---|---|
| `mytimalove.com` / `www` | `149.56.140.166` | Site Django |
| `mail.mytimalove.com` | `109.234.167.76` | Serveur mail Namecheap |
| `timalove.goo-bridge.com` | `173.249.41.61` | Autre serveur (ne pas utiliser pour SMTP si la boîte est chez Namecheap) |

**À faire pour que le reset de mot de passe fonctionne :**

1. Dans le **cPanel Namecheap** du compte qui héberge vraiment les mails, créez une boîte du type `service@mytimalove.com` (ou `noreply@mytimalove.com`).
2. Dans « Email Accounts → Connect Devices », notez le **Outgoing Server** réel (souvent `mail.mytimalove.com` ou un hostname `*.web-hosting.com`), port **465** SSL.
3. Dans `timalove/.env` (local + VPS) :
   ```env
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=mail.mytimalove.com
   EMAIL_PORT=465
   EMAIL_HOST_USER=service@mytimalove.com
   EMAIL_HOST_PASSWORD=VOTRE_MOT_DE_PASSE_CPANEL
   EMAIL_USE_SSL=True
   EMAIL_USE_TLS=False
   DEFAULT_FROM_EMAIL=TimaLove <service@mytimalove.com>
   ```
4. Vérifiez que les DNS mail (`A mail`, MX, SPF) restent sur Namecheap — **ne pointez pas** `mail` vers le VPS Django sauf si vous y migrez Postfix/Exim.
5. Redémarrez Daphne puis testez : page `/mot-de-passe-oublie/` ou un `send_mail` Django.

Évitez `EMAIL_HOST=timalove.goo-bridge.com` tant que ce nom résout vers un **autre** VPS que celui où la boîte a été créée (erreur typique `535 Incorrect authentication data`).

---

## 2. Installation sur le VPS

Connexion SSH :

```bash
ssh jomas@VOTRE_IP_VPS -p22
```

Lancer l’installateur (depuis GitHub `main`) :

```bash
curl -fsSL https://raw.githubusercontent.com/nick-dev12/timalove/main/deploy/install-vps.sh \
  -o /tmp/install-vps.sh

sudo bash /tmp/install-vps.sh \
  --domain mytimalove.com \
  --email admin@mytimalove.com \
  --app-user jomas
```

### Options utiles

```bash
sudo bash /tmp/install-vps.sh --help

# Forcer SSL pendant l’install (DNS déjà prêt)
sudo bash /tmp/install-vps.sh --domain mytimalove.com --ssl

# Sans Certbot
sudo bash /tmp/install-vps.sh --domain mytimalove.com --skip-ssl

# Mot de passe PostgreSQL choisi à l’avance
sudo bash /tmp/install-vps.sh --db-password 'VotreMotDePasseFort'
```

### Ce que fait le script

1. Installe Python, PostgreSQL, Redis, Nginx, Certbot, UFW  
2. Crée la base `timalove` et l’utilisateur DB  
3. Configure Redis (Channels + Celery)  
4. Clone `https://github.com/nick-dev12/timalove.git` → `/home/jomas/timalove`  
5. Crée le venv, `pip install`, `.env`, migrations, `collectstatic`  
6. Active les services systemd : `daphne-timalove`, `celery-timalove`, `celerybeat-timalove`  
7. Configure Nginx (proxy HTTP + WebSocket)  
8. Tente le SSL si le DNS pointe déjà vers le VPS  

Durée typique : **5–15 minutes**.

---

## 3. SSL (si pas fait automatiquement)

Quand `nslookup mytimalove.com` renvoie l’IP du VPS :

```bash
sudo bash /home/jomas/timalove/deploy/enable-ssl.sh
```

Puis dans Cloudflare : SSL/TLS → **Full (strict)**.

---

## 4. Finaliser la config métier

```bash
sudo nano /home/jomas/timalove/timalove/.env
```

À renseigner au minimum :

- Clés **NabooPay** / CinetPay  
- **Resend** (email)  
- **Firebase** (push)  
- reCAPTCHA si utilisé  

Copier les fichiers secrets hors git dans `/home/jomas/timalove/timalove/` :

- `timalove-ddaa5-*.json` (Firebase Admin)  
- `AuthKey_*.p8` (Apple Sign-In, si besoin)  

Créer le super-admin :

```bash
sudo -u jomas bash -lc '
  cd /home/jomas/timalove/timalove &&
  source ../venv/bin/activate &&
  python manage.py createsuperuser
'
```

Admin web : `https://mytimalove.com/espace-prive/connexion/`

---

## 5. Mises à jour — utilisez toujours `deploy.sh`

**Oui : après l’install, c’est le script officiel pour chaque mise à jour.**

```bash
# Depuis le PC : push sur GitHub d’abord
git push origin main

# Sur le VPS :
sudo bash /home/jomas/timalove/timalove/deploy.sh
```

### Ce que fait un deploy « complet » (sans option)

| Étape | Action |
|-------|--------|
| 1 | `git pull` |
| 2 | `pip install -r requirements.txt` |
| 3 | `migrate` |
| 4 | `collectstatic` (+ contrôle que staticfiles n’est pas vide) |
| 5 | Restart `daphne` / `celery` / `celerybeat` + reload Nginx |
| Checks | Redis PONG, PostgreSQL, port 8001, HTTP site, CSS static, `check --deploy`, Celery ping, **WebSocket + push/FCM** (`verify_runtime.py`), NabooPay si clé présente |

Si le DNS du domaine ne pointe pas encore vers le VPS, les checks HTTP utilisent automatiquement `http://IP`.

### Options utiles

```bash
# Avant d’avoir configuré NabooPay
sudo bash /home/jomas/timalove/timalove/deploy.sh --skip-naboopay

# Échoue si un WARN apparaît (CI / prod stricte)
sudo bash /home/jomas/timalove/timalove/deploy.sh --strict

# CSS/JS seulement (pas de restart ni checks lourds)
sudo bash /home/jomas/timalove/timalove/deploy.sh --fast

sudo bash /home/jomas/timalove/timalove/deploy.sh --help
```

> Ne pas utiliser `--no-checks` en production sauf urgence.  
> Ne pas lancer `install-vps.sh` à chaque update — seulement `deploy.sh`.

Les chemins sont lus depuis `/etc/timalove/deploy.env` + `SITE_URL` dans `timalove/.env`.

---

## 6. Commandes utiles

```bash
# État des services
systemctl status daphne-timalove celery-timalove celerybeat-timalove redis-server nginx

# Logs temps réel
journalctl -u daphne-timalove -f
journalctl -u celery-timalove -f

# Redis
redis-cli ping

# Test local Daphne
curl -I -H "Host: mytimalove.com" http://127.0.0.1:8001/
```

---

## Dépannage

| Symptôme | Piste |
|----------|--------|
| Site inaccessible / mauvais contenu | DNS Cloudflare encore sur Vercel → vérifier les A records |
| Certbot échoue | DNS pas encore propagé, ou proxy orange actif → passer en DNS only |
| 502 Bad Gateway | `systemctl status daphne-timalove` + `journalctl -u daphne-timalove -n 80` |
| WebSocket / chat KO | Redis down, ou `USE_REDIS_CHANNELS=True` manquant dans `.env` |
| Erreur migrate PostgreSQL | Mot de passe DB / droits : voir `.env` (`DB_*`) |
| Celery inactif | `journalctl -u celery-timalove -n 50` ; Redis doit répondre `PONG` |

---

## Architecture runtime

```
Internet → Cloudflare → Nginx (80/443)
                           ├─ /static/, /media/  (fichiers)
                           ├─ /ws/               → Daphne :8001 (WebSocket)
                           └─ /                  → Daphne :8001 (HTTP ASGI)

Daphne / Celery / Celery Beat
    ├─ PostgreSQL 127.0.0.1:5432
    └─ Redis      127.0.0.1:6379  (Channels + broker)
```
