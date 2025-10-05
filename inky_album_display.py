#!/usr/bin/env python3
"""
Script principal: Album du jour sur Inky Impression
Combine Spotify API + génération d'image + affichage e-ink
"""

import os
import sys
from spotify_integration import SpotifyAlbumFetcher
from inky_album_display import create_album_display, display_on_inky


def main():
    """Fonction principale"""
    print("═" * 60)
    print("  🎵 ALBUM DU JOUR - INKY IMPRESSION 7.3\"")
    print("═" * 60)
    
    # Charger les credentials depuis .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
    CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
    PLAYLIST_ID = os.getenv('SPOTIFY_PLAYLIST_ID')
    
    # Vérifications
    if not CLIENT_ID or not CLIENT_SECRET:
        print("\n❌ SPOTIFY_CLIENT_ID et SPOTIFY_CLIENT_SECRET requis!")
        print("   Configure ton fichier .env ou les variables d'environnement\n")
        sys.exit(1)
    
    if not PLAYLIST_ID:
        print("\n❌ SPOTIFY_PLAYLIST_ID requis!")
        print("   Ajoute l'ID de ta playlist dans le .env\n")
        sys.exit(1)
    
    try:
        # Étape 1: Récupérer un album aléatoire depuis Spotify
        print("\n[1/3] Connexion à Spotify...")
        fetcher = SpotifyAlbumFetcher(CLIENT_ID, CLIENT_SECRET)
        
        print("\n[2/3] Sélection d'un album aléatoire...")
        album_data = fetcher.get_random_album_from_playlist(PLAYLIST_ID)
        
        if not album_data:
            print("\n❌ Impossible de récupérer un album")
            sys.exit(1)
        
        print(f"\n✓ Album choisi: {album_data['title']} - {album_data['artist']}")
        
        # Étape 2: Générer l'image
        print("\n[3/3] Génération de l'image...")
        img = create_album_display(album_data)
        
        # Sauvegarder
        output_path = 'album_du_jour.png'  # Ajuste le chemin si besoin
        img.save(output_path)
        print(f"✓ Image sauvegardée: {output_path}")
        
        # Étape 3: Afficher sur l'écran Inky
        print("\n[4/3] Affichage sur Inky Impression...")
        display_on_inky(img)
        
        print("\n" + "═" * 60)
        print("  ✓ TERMINÉ!")
        print("═" * 60)
        
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