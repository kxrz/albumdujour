#!/usr/bin/env python3
"""
Script principal pour Raspberry Pi - Album du jour sur Inky Impression
Génère l'image et l'affiche sur l'écran e-ink
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
    'DARK_GRAY': (40, 40, 40),
    'ORANGE': (255, 165, 0),
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
    cover = cover.resize((size, size), Image.LANCZOS)
    
    palette_img = Image.new('P', (1, 1))
    palette = [
        0, 0, 0,
        255, 255, 255,
        255, 0, 0,
        0, 255, 0,
        0, 0, 255,
        255, 255, 0,
        255, 165, 0,
    ]
    palette += [0] * (768 - len(palette))
    palette_img.putpalette(palette)
    
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
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
    ]
    
    for font_path in fonts_to_try:
        try:
            return ImageFont.truetype(font_path, size)
        except:
            continue
    
    print(f"Impossible de charger une police système, utilisation de la police par défaut")
    return ImageFont.load_default()


def create_album_display(album_data: Dict) -> Image.Image:
    """Crée l'image complète de l'album du jour"""
    print("\n[Génération de l'image]")
    
    img = Image.new('RGB', (WIDTH, HEIGHT), COLORS['WHITE'])
    draw = ImageDraw.Draw(img)
    
    # === PARTIE GAUCHE: COVER ===
    print("  → Fond et cover...")
    draw.rectangle([0, 0, COVER_WIDTH, HEIGHT], fill=COLORS['DARK_GRAY'])
    
    cover = None
    if album_data.get('cover_url'):
        print(f"  → Téléchargement cover...")
        cover = download_image(album_data['cover_url'])
        if cover:
            print("  → Application du dithering...")
            cover = process_cover_for_eink(cover, size=300)
    
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
    
    img.paste(cover, (30, 90))
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
    
    bbox_music = draw.textbbox((0, 0), music_symbol, font=badge_font_music)
    music_width = bbox_music[2] - bbox_music[0]
    
    bbox_text = draw.textbbox((0, 0), badge_text_only, font=badge_font)
    text_width = bbox_text[2] - bbox_text[0]
    badge_height = bbox_text[3] - bbox_text[1] + 14
    
    total_badge_width = music_width + text_width + 40
    draw.rectangle(
        [x_start, y_pos, x_start + total_badge_width, y_pos + badge_height],
        fill=COLORS['RED']
    )
    
    draw.text(
        (x_start + 12, y_pos + 3),
        music_symbol,
        fill=COLORS['WHITE'],
        font=badge_font_music
    )
    
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
    
    max_title_width = INFO_WIDTH - 70 - 100
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
    draw.text((x_start, y_pos), "MEILLEURS TITRES DE L'ALBUM :", fill=COLORS['BLACK'], font=font_tracks_title)
    
    y_pos += 30
    
    # Tracks (max 5)
    font_track_num = load_font(14, bold=True)
    font_track_name = load_font(14)
    font_asterisk = load_font(18, bold=True)
    
    tracks = album_data.get('tracks', [])[:5]
    max_track_width = max_title_width - 35
    
    for i, track_data in enumerate(tracks, 1):
        if isinstance(track_data, dict):
            track_name = track_data['name']
            in_playlist = track_data.get('in_playlist', False)
        else:
            track_name = track_data
            in_playlist = False
        
        track_num = f"{i:02d}"
        draw.text((x_start, y_pos), track_num, fill=COLORS['BLACK'], font=font_track_num)
        
        track_x = x_start + 34
        
        available_width = max_track_width - 25 if in_playlist else max_track_width
        track_name_truncated = truncate_text(track_name, available_width, font_track_name, draw)
        
        draw.text((track_x, y_pos), track_name_truncated, fill=COLORS['BLACK'], font=font_track_name)
        
        if in_playlist:
            bbox = draw.textbbox((track_x, y_pos), track_name_truncated, font=font_track_name)
            asterisk_x = bbox[2] + 8
            draw.text((asterisk_x, y_pos - 2), "*", fill=COLORS['ORANGE'], font=font_asterisk)
        
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


def display_on_inky(img: Image.Image):
    """Affiche l'image sur l'écran Inky Impression"""
    try:
        from inky.auto import auto
        
        print("  → Détection automatique de l'écran Inky...")
        
        # Détection automatique de l'écran (comme dans ton poster.py)
        inky = auto(ask_user=False, verbose=True)
        
        print(f"  → Écran détecté: {inky.resolution[0]}x{inky.resolution[1]}")
        
        # Redimensionner l'image si nécessaire
        if img.size != inky.resolution:
            print(f"  → Redimensionnement: {img.size} → {inky.resolution}")
            img = img.resize(inky.resolution, Image.LANCZOS)
        
        print("  → Envoi de l'image à l'écran...")
        try:
            inky.set_image(img, saturation=0.5)
        except TypeError:
            # Certains modèles ne supportent pas le paramètre saturation
            inky.set_image(img)
        
        print("  → Rafraîchissement de l'écran (cela peut prendre ~30 secondes)...")
        inky.show()
        
        print("  ✓ Image affichée sur l'écran Inky!")
        
    except ImportError:
        print("⚠️  Module 'inky' non disponible")
        print("   Installation: pip install inky[rpi]")
    except Exception as e:
        print(f"❌ Erreur affichage Inky: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Fonction principale"""
    print("=" * 70)
    print("  🎵 ALBUM DU JOUR - INKY IMPRESSION")
    print("=" * 70)
    
    # Charger .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
    CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
    PLAYLIST_ID = os.getenv('SPOTIFY_PLAYLIST_ID')
    
    if not all([CLIENT_ID, CLIENT_SECRET, PLAYLIST_ID]):
        print("\n❌ Configure ton .env d'abord!")
        print("   SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_PLAYLIST_ID requis")
        sys.exit(1)
    
    try:
        # Récupérer album depuis Spotify
        print("\n[1/3] Récupération depuis Spotify...")
        fetcher = SpotifyAlbumFetcher(CLIENT_ID, CLIENT_SECRET)
        album_data = fetcher.get_random_album_from_playlist(PLAYLIST_ID)
        
        if not album_data:
            print("❌ Impossible de récupérer l'album")
            sys.exit(1)
        
        # Générer l'image
        print("\n[2/3] Génération de l'image...")
        img = create_album_display(album_data)
        
        # Sauvegarder
        output_path = '/home/pi/album_du_jour.png'
        img.save(output_path)
        print(f"✓ Image sauvegardée: {output_path}")
        
        # Afficher sur Inky
        print("\n[3/3] Affichage sur l'écran...")
        display_on_inky(img)
        
        print("\n" + "=" * 70)
        print("  ✓ TERMINÉ!")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interruption par l'utilisateur")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()