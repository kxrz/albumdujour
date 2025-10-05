#!/usr/bin/env python3
"""
Script de test pour macOS - Génère l'image sans Inky
Teste la génération d'image + intégration Spotify
"""

import os
import sys
import io
import requests
from PIL import Image, ImageDraw, ImageFont
import qrcode
from datetime import datetime
from typing import Dict, List, Optional

# Import du module Spotify
from spotify_integration import SpotifyAlbumFetcher

# Configuration Inky Impression
WIDTH = 800
HEIGHT = 480
COVER_WIDTH = 360
INFO_WIDTH = 440

# Palette Inky Impression PIM773
COLORS = {
    'BLACK': (0, 0, 0),
    'WHITE': (255, 255, 255),
    'RED': (255, 0, 0),
    'DARK_GRAY': (40, 40, 40),  # Fond pour la cover
    'ORANGE': (255, 165, 0),     # Pour l'astérisque
}

# Mois en français
MOIS = {
    1: 'janvier', 2: 'février', 3: 'mars', 4: 'avril',
    5: 'mai', 6: 'juin', 7: 'juillet', 8: 'août',
    9: 'septembre', 10: 'octobre', 11: 'novembre', 12: 'décembre'
}


def truncate_text(text: str, max_width: int, font: ImageFont.FreeTypeFont, draw: ImageDraw.Draw) -> str:
    """Tronque le texte avec ... si trop long"""
    if draw.textbbox((0, 0), text, font=font)[2] <= max_width:
        return text
    
    while draw.textbbox((0, 0), text + '...', font=font)[2] > max_width and len(text) > 0:
        text = text[:-1]
    
    return text + '...' if text else '...'


def format_date(date_str: str) -> str:
    """Formate une date en année uniquement (ex: '1971-09-24' -> '1971')"""
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        return str(date.year)
    except:
        # Si la date est déjà juste une année
        if date_str and len(date_str) >= 4:
            return date_str[:4]
        return date_str


def download_image(url: str) -> Optional[Image.Image]:
    """Télécharge une image depuis une URL"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content))
    except Exception as e:
        print(f"Erreur téléchargement image: {e}")
        return None


def process_cover_for_eink(cover: Image.Image, size: int = 300) -> Image.Image:
    """
    Traite la cover pour l'e-ink avec dithering
    Réduit aux 7 couleurs de l'Inky Impression
    """
    # Redimensionner
    cover = cover.resize((size, size), Image.LANCZOS)
    
    # Convertir en palette limitée avec dithering
    palette_img = Image.new('P', (1, 1))
    palette = [
        0, 0, 0,        # Noir
        255, 255, 255,  # Blanc
        255, 0, 0,      # Rouge
        0, 255, 0,      # Vert
        0, 0, 255,      # Bleu
        255, 255, 0,    # Jaune
        255, 165, 0,    # Orange
    ]
    # Compléter la palette à 256 couleurs
    palette += [0] * (768 - len(palette))
    palette_img.putpalette(palette)
    
    # Convertir avec dithering
    cover = cover.convert('RGB')
    cover = cover.quantize(palette=palette_img, dither=Image.FLOYDSTEINBERG)
    cover = cover.convert('RGB')
    
    return cover


def generate_qr_code(url: str, size: int = 100) -> Image.Image:
    """Génère un QR code pour l'URL Spotify"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=3,
        border=1,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color=COLORS['BLACK'], back_color=COLORS['WHITE'])
    qr_img = qr_img.resize((size, size), Image.NEAREST)
    
    return qr_img


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Charge une police avec gestion des fallbacks"""
    fonts_to_try = [
        # macOS
        '/System/Library/Fonts/Helvetica.ttc',
        '/System/Library/Fonts/Supplemental/Arial.ttf',
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf' if bold else '/System/Library/Fonts/Supplemental/Arial.ttf',
        # Linux
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        # Windows
        'C:\\Windows\\Fonts\\arial.ttf',
        'C:\\Windows\\Fonts\\arialbd.ttf' if bold else 'C:\\Windows\\Fonts\\arial.ttf',
    ]
    
    for font_path in fonts_to_try:
        try:
            return ImageFont.truetype(font_path, size)
        except:
            continue
    
    # Fallback vers la police par défaut
    print(f"⚠️  Impossible de charger une police système, utilisation de la police par défaut")
    return ImageFont.load_default()


def create_album_display(album_data: Dict) -> Image.Image:
    """
    Crée l'image complète de l'album du jour
    
    album_data doit contenir:
    - title: titre de l'album
    - artist: nom de l'artiste
    - release_date: date de sortie (format YYYY-MM-DD)
    - cover_url: URL de la pochette
    - tracks: liste des titres (strings)
    - spotify_url: URL Spotify de l'album
    """
    print("\n[Génération de l'image]")
    
    # Créer l'image de base
    img = Image.new('RGB', (WIDTH, HEIGHT), COLORS['WHITE'])
    draw = ImageDraw.Draw(img)
    
    # === PARTIE GAUCHE: COVER ===
    print("  → Fond bleu et cover...")
    # Fond gris foncé
    draw.rectangle([0, 0, COVER_WIDTH, HEIGHT], fill=COLORS['DARK_GRAY'])
    
    # Télécharger et traiter la cover
    cover = None
    if album_data.get('cover_url'):
        print(f"  → Téléchargement: {album_data['cover_url'][:50]}...")
        cover = download_image(album_data['cover_url'])
        if cover:
            print("  → Application du dithering...")
            cover = process_cover_for_eink(cover, size=300)
    
    # Placeholder si pas de cover
    if not cover:
        print("  → Création d'un placeholder...")
        cover = Image.new('RGB', (300, 300), COLORS['BLACK'])
        draw_cover = ImageDraw.Draw(cover)
        font_placeholder = load_font(14, bold=True)
        text = "COVER\nIMAGE"
        bbox = draw_cover.textbbox((0, 0), text, font=font_placeholder)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        draw_cover.text(
            ((300 - text_width) // 2, (300 - text_height) // 2),
            text,
            fill=COLORS['WHITE'],
            font=font_placeholder,
            align='center'
        )
    
    # Coller la cover
    img.paste(cover, (30, 90))
    
    # Border blanche autour de la cover
    draw.rectangle([30, 90, 330, 390], outline=COLORS['WHITE'], width=4)
    
    # Date sous la cover
    print("  → Ajout de la date...")
    font_date = load_font(14, bold=True)
    date_text = format_date(album_data.get('release_date', ''))
    date_text = truncate_text(date_text, 300, font_date, draw)
    bbox = draw.textbbox((0, 0), date_text, font=font_date)
    date_width = bbox[2] - bbox[0]
    draw.text(
        ((COVER_WIDTH - date_width) // 2, 410),
        date_text,
        fill=COLORS['WHITE'],
        font=font_date
    )
    
    # === PARTIE DROITE: INFOS ===
    print("  → Ajout des métadonnées...")
    x_start = COVER_WIDTH + 35
    y_pos = 40
    
    # Badge "Album du jour"
    badge_font = load_font(11, bold=True)
    badge_font_music = load_font(16, bold=True)
    
    music_symbol = "♪"
    badge_text_only = "ALBUM DU JOUR"
    
    # Calculer les dimensions
    bbox_music = draw.textbbox((0, 0), music_symbol, font=badge_font_music)
    music_width = bbox_music[2] - bbox_music[0]
    
    bbox_text = draw.textbbox((0, 0), badge_text_only, font=badge_font)
    text_width = bbox_text[2] - bbox_text[0]
    badge_height = bbox_text[3] - bbox_text[1] + 14
    
    # Dessiner le fond du badge
    total_badge_width = music_width + text_width + 40
    draw.rectangle(
        [x_start, y_pos, x_start + total_badge_width, y_pos + badge_height],
        fill=COLORS['RED']
    )
    
    # Dessiner le symbole musical plus grand
    draw.text(
        (x_start + 12, y_pos + 3),
        music_symbol,
        fill=COLORS['WHITE'],
        font=badge_font_music
    )
    
    # Dessiner le texte
    draw.text(
        (x_start + 12 + music_width + 8, y_pos + 7),
        badge_text_only,
        fill=COLORS['WHITE'],
        font=badge_font
    )
    
    y_pos += badge_height + 22
    
    # Titre de l'album
    font_title = load_font(38, bold=True)
    title = album_data.get('title', 'Album')
    
    # Gérer les titres longs (max 2 lignes)
    max_title_width = INFO_WIDTH - 70 - 100  # Espace pour QR code
    title_lines = []
    words = title.split()
    current_line = ""
    
    for word in words:
        test_line = current_line + " " + word if current_line else word
        bbox = draw.textbbox((0, 0), test_line, font=font_title)
        if bbox[2] - bbox[0] <= max_title_width:
            current_line = test_line
        else:
            if current_line:
                title_lines.append(current_line)
            current_line = word
    
    if current_line:
        title_lines.append(current_line)
    
    # Limiter à 2 lignes
    if len(title_lines) > 2:
        title_lines = title_lines[:2]
        title_lines[1] = truncate_text(title_lines[1], max_title_width, font_title, draw)
    
    for line in title_lines:
        draw.text((x_start, y_pos), line, fill=COLORS['BLACK'], font=font_title)
        y_pos += 44
    
    # Nom de l'artiste
    font_artist = load_font(24)
    artist = album_data.get('artist', 'Artiste')
    artist = truncate_text(artist, max_title_width, font_artist, draw)
    draw.text((x_start, y_pos), artist, fill=COLORS['BLACK'], font=font_artist)
    y_pos += 44
    
    # Séparateur
    draw.line(
        [x_start, y_pos, x_start + max_title_width, y_pos],
        fill=COLORS['BLACK'],
        width=3
    )
    y_pos += 22
    
    # Section des tracks
    print("  → Ajout des tracks...")
    font_tracks_title = load_font(12, bold=True)
    draw.text((x_start, y_pos), "MEILLEURS TITRES DE L'ALBUM", fill=COLORS['BLACK'], font=font_tracks_title)
    
    # Ligne sous le titre
    draw.line(
        [x_start, y_pos + 16, x_start + 150, y_pos + 16],
        fill=COLORS['WHITE'],
        width=2
    )
    y_pos += 28
    
    # Tracks (max 5)
    print("  → Ajout des tracks...")
    font_track_num = load_font(14, bold=True)
    font_track_name = load_font(14)
    font_asterisk = load_font(18, bold=True)  # Plus gros pour l'astérisque
    
    tracks = album_data.get('tracks', [])[:5]
    max_track_width = max_title_width - 35
    
    print(f"     Tracks reçus: {tracks}")
    
    for i, track_data in enumerate(tracks, 1):
        # Gérer le cas où track est un dict ou un string
        if isinstance(track_data, dict):
            track_name = track_data['name']
            in_playlist = track_data.get('in_playlist', False)
            print(f"     [{i}] {track_name} - in_playlist: {in_playlist}")
        else:
            track_name = track_data
            in_playlist = False
            print(f"     [{i}] {track_name} - (format string, in_playlist: False)")
        
        # Numéro de track
        track_num = f"{i:02d}"
        draw.text((x_start, y_pos), track_num, fill=COLORS['BLACK'], font=font_track_num)
        
        # Nom de la track
        track_x = x_start + 34
        
        # Si c'est le track de la playlist, réserver de l'espace pour l'astérisque à la fin
        available_width = max_track_width - 25 if in_playlist else max_track_width
        track_name_truncated = truncate_text(track_name, available_width, font_track_name, draw)
        
        draw.text((track_x, y_pos), track_name_truncated, fill=COLORS['BLACK'], font=font_track_name)
        
        # Ajouter l'astérisque orange à la fin si c'est le track de la playlist
        if in_playlist:
            bbox = draw.textbbox((track_x, y_pos), track_name_truncated, font=font_track_name)
            asterisk_x = bbox[2] + 8
            draw.text((asterisk_x, y_pos - 2), "***", fill=COLORS['ORANGE'], font=font_asterisk)
        
        y_pos += 25
    
    # === QR CODE ===
    print("  → Génération du QR code...")
    if album_data.get('spotify_url'):
        qr_img = generate_qr_code(album_data['spotify_url'], size=100)
        qr_x = WIDTH - 135
        qr_y = HEIGHT - 140
        img.paste(qr_img, (qr_x, qr_y))
    
    print("  ✓ Image générée!\n")
    return img


    def get_random_album_from_playlist(self, playlist_id: str) -> Optional[Dict]:
        """
        Sélectionne un album aléatoire depuis une playlist
        
        Args:
            playlist_id: ID ou URL de la playlist (doit être publique!)
            
        Returns:
            Dictionnaire avec toutes les infos de l'album pour create_album_display()
        """
        # Extraire l'ID si c'est une URL complète
        if 'spotify.com/playlist/' in playlist_id:
            playlist_id = playlist_id.split('playlist/')[-1].split('?')[0]
        
        print(f"Récupération de la playlist {playlist_id}...")
        
        # Récupérer tous les tracks de la playlist
        playlist_tracks = []
        offset = 0
        limit = 100
        
        while True:
            results = self.sp.playlist_tracks(
                playlist_id,
                offset=offset,
                limit=limit,
                fields='items(track(id,name,album(id))),next'
            )
            
            if not results['items']:
                break
            
            for item in results['items']:
                if item['track']:
                    playlist_tracks.append({
                        'track_id': item['track']['id'],
                        'track_name': item['track']['name'],
                        'album_id': item['track']['album']['id']
                    })
            
            if not results['next']:
                break
            
            offset += limit
        
        if not playlist_tracks:
            print("Aucun track trouvé dans la playlist")
            return None
        
        # Choisir un track aléatoire
        selected_track = random.choice(playlist_tracks)
        album_id = selected_track['album_id']
        playlist_track_name = selected_track['track_name']
        
        print(f"\n🎵 Track sélectionné: {playlist_track_name}")
        
        # Récupérer l'album complet
        album = self.sp.album(album_id)
        
        # Récupérer les tracks avec popularité
        track_ids = [t['id'] for t in album['tracks']['items'] if t['id']]
        
        detailed_tracks = []
        for i in range(0, len(track_ids), 50):
            batch = track_ids[i:i+50]
            track_details = self.sp.tracks(batch)
            detailed_tracks.extend(track_details['tracks'])
        
        # Trier par popularité
        detailed_tracks.sort(key=lambda x: x.get('popularity', 0), reverse=True)
        
        # Marquer le track qui vient de la playlist
        tracks_with_metadata = []
        for t in detailed_tracks[:5]:
            tracks_with_metadata.append({
                'name': t['name'],
                'in_playlist': t['name'].lower() == playlist_track_name.lower()
            })
        
        print(f"📀 Album: {album['name']} - {album['artists'][0]['name']}")
        
        return {
            'title': album['name'],
            'artist': album['artists'][0]['name'] if album['artists'] else 'Unknown',
            'release_date': album['release_date'],
            'cover_url': album['images'][0]['url'] if album['images'] else None,
            'tracks': tracks_with_metadata,
            'spotify_url': album['external_urls']['spotify']
        }


def main():
    """Test sur macOS"""
    print("═" * 60)
    print("  🎵 TEST ALBUM DU JOUR - macOS")
    print("═" * 60)
    
    # Charger .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️  python-dotenv non installé")
    
    CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
    CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
    PLAYLIST_ID = os.getenv('SPOTIFY_PLAYLIST_ID')
    
    if not all([CLIENT_ID, CLIENT_SECRET, PLAYLIST_ID]):
        print("\n❌ Configure ton .env d'abord!")
        sys.exit(1)
    
    try:
        # Récupérer album depuis Spotify
        print("\n[1/2] Récupération depuis Spotify...")
        fetcher = SpotifyAlbumFetcher(CLIENT_ID, CLIENT_SECRET)
        album_data = fetcher.get_random_album_from_playlist(PLAYLIST_ID)
        
        if not album_data:
            print("❌ Impossible de récupérer l'album")
            sys.exit(1)
        
        # Générer l'image
        print("\n[2/2] Génération de l'image...")
        img = create_album_display(album_data)
        
        # Sauvegarder dans le dossier courant
        output_path = 'album_du_jour.png'
        img.save(output_path)
        print(f"✓ Image sauvegardée: {output_path}")
        
        # Ouvrir automatiquement sur macOS
        try:
            import subprocess
            subprocess.run(['open', output_path])
            print("✓ Image ouverte!")
        except:
            print("  (Ouvre l'image manuellement)")
        
        print("\n" + "═" * 60)
        print("  ✓ TEST TERMINÉ!")
        print("═" * 60)
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()