# 🎵 Album du jour - Inky Impression 7.3"

![Affichage de l'album du jour sur un PIM773](pimonori.png "Titre de l'image")

Configuration complète pour afficher un album aléatoire depuis ta playlist Spotify sur ton écran e-ink.

```bash
Il est possible de tester dans le terminal sur un Macbook le script en utilisant macos.py à la place de main.py
```

---

## 📦 Installation

### 1. Prérequis système (Raspberry Pi)

```bash
# Mise à jour du système
sudo apt-get update
sudo apt-get upgrade -y

# Installation des dépendances système
sudo apt-get install -y python3-pip python3-pil python3-numpy git
```

### 2. Installation des bibliothèques Python

```bash
# Créer un environnement virtuel (recommandé)
python3 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install --upgrade pip
pip install Pillow requests qrcode[pil] spotipy python-dotenv

# Installer la bibliothèque Inky
pip install inky[rpi]
```

---

## 🔑 Configuration Spotify API

### Étape 1: Créer une application Spotify

1. Va sur **https://developer.spotify.com/dashboard** (depuis ton PC)
2. Connecte-toi avec ton compte Spotify
3. Clique sur **"Create app"**
4. Remplis le formulaire :
   - **App name:** `Album du jour Inky`
   - **App description:** `Display pour Raspberry Pi`
   - **Redirect URI:** `http://localhost:8888/callback` (pas utilisé mais obligatoire)
   - Coche **"Web API"**
5. Clique sur **"Save"**
6. Dans la page de ton app, clique sur **"Settings"**
7. Note ton **Client ID** et **Client Secret**

### Étape 2: Créer et configurer ta playlist

1. Crée une playlist sur Spotify avec tes albums préférés
2. **IMPORTANT:** Rends-la **PUBLIQUE** (sinon ça ne marchera pas en mode headless)
   - Clique sur les 3 points de ta playlist
   - "Make public"
3. Clique sur **"..."** puis **"Partager"** > **"Copier le lien"**
4. L'ID est la partie après `/playlist/` dans l'URL

**Exemple:**
```
https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
                                 └─────────────┬───────┘
                                               │
                                          C'est ton ID!
```

### Étape 3: Créer le fichier .env

Sur ton Raspberry Pi en SSH :

```bash
cd ~/album-du-jour
nano .env
```

Et ajoute tes credentials :

```env
SPOTIFY_CLIENT_ID=ton_client_id_ici
SPOTIFY_CLIENT_SECRET=ton_client_secret_ici
SPOTIFY_PLAYLIST_ID=ton_playlist_id_ici
```

**Sauvegarde avec Ctrl+O puis Entrée, quitte avec Ctrl+X**

**⚠️ Important:** 
- Ta playlist DOIT être publique
- Pas besoin d'authentification utilisateur en mode headless
- Le script utilise Client Credentials Flow (pas de navigateur nécessaire)

---

## 📁 Structure du projet

```
album-du-jour/
├── .env                      # Credentials Spotify (à créer)
├── main.py                   # Script principal
├── spotify_integration.py    # Module Spotify API
├── inky_album_display.py     # Module génération d'image
├── album_du_jour.png         # Image générée (créée automatiquement)
└── README.md                 # Ce fichier
```

---

## 🚀 Utilisation

### Exécution du script (en SSH)

```bash
python3 main.py
```

Le script va :
1. ✅ Se connecter à Spotify (Client Credentials, pas de navigateur!)
2. ✅ Récupérer ta playlist publique
3. ✅ Choisir un album aléatoire
4. ✅ Télécharger la pochette
5. ✅ Générer l'image avec QR code
6. ✅ Afficher sur l'écran Inky

**Aucune interaction requise, tout se passe en terminal!**

---

## ⏰ Automatisation avec cron (optionnel)

Pour mettre à jour l'album tous les jours à 00h00 :

```bash
# Ouvrir le crontab
crontab -e

# Ajouter cette ligne (ajuste le chemin!)
0 0 * * * cd /home/pi/album-du-jour && /home/pi/album-du-jour/venv/bin/python3 main.py >> /home/pi/album-du-jour/logs.txt 2>&1
```

---

## 🐛 Dépannage

### Erreur "No module named 'inky'"

```bash
pip install inky[rpi]
```

### Erreur "Failed to open device"

L'écran Inky n'est pas détecté. Vérifie :
- Que l'écran est bien connecté au GPIO
- Que l'interface SPI est activée : `sudo raspi-config` > Interface Options > SPI > Enable

### Erreur d'authentification Spotify

Si tu as l'erreur "Invalid client" ou "HTTP 401":
1. Vérifie que ton Client ID et Client Secret sont corrects dans le `.env`
2. Vérifie que ta playlist est bien **publique**
3. L'app Spotify doit avoir "Web API" coché dans les settings

### Image floue ou mal rendue

Le dithering Floyd-Steinberg est appliqué automatiquement. Tu peux ajuster la fonction `process_cover_for_eink()` dans `inky_album_display.py`.

### Playlist privée

Le mode headless (SSH) ne supporte que les playlists **publiques**. Si tu veux absolument utiliser une playlist privée, tu devras :
1. Configurer l'authentification OAuth depuis ton PC
2. Copier le fichier `.cache` généré sur ton Pi
3. Ce n'est pas recommandé pour l'automatisation

---

## 🎨 Personnalisation

### Changer le nombre de tracks affichés

Dans `inky_album_display.py`, ligne 244 :

```python
tracks = album_data.get('tracks', [])[:5]  # Modifier ici
```

### Modifier les couleurs

Dans `inky_album_display.py`, dictionnaire `COLORS` :

```python
COLORS = {
    'BLACK': (0, 0, 0),
    'WHITE': (255, 255, 255),
    'RED': (255, 0, 0),
    'BLUE': (29, 53, 87),
}
```

### Changer la taille du QR code

Dans `inky_album_display.py`, ligne ~268 :

```python
qr_img = generate_qr_code(album_data['spotify_url'], size=100)  # Modifier size
```

---

## 📝 Notes

- **Résolution écran:** 800 x 480 pixels (127 PPI)
- **Palette:** 7 couleurs (noir, blanc, rouge, vert, bleu, jaune, orange)
- **Rafraîchissement:** ~30 secondes pour un affichage complet
- **Durée de vie:** Les écrans e-ink peuvent supporter des millions de rafraîchissements

---

## 🔗 Ressources

- [Documentation Inky Impression](https://learn.pimoroni.com/article/getting-started-with-inky-impression)
- [Spotify Web API](https://developer.spotify.com/documentation/web-api)
- [Spotipy Documentation](https://spotipy.readthedocs.io/)

---

## 📄 Licence

Ce projet est libre d'utilisation pour un usage personnel.

**Enjoy! 🎶**
