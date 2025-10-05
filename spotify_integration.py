#!/usr/bin/env python3
"""
Intégration Spotify pour récupérer un album aléatoire depuis une playlist
"""

import os
import random
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from typing import Dict, List, Optional


class SpotifyAlbumFetcher:
    """Récupère les informations d'albums depuis Spotify"""
    
    def __init__(self, client_id: str, client_secret: str):
        """
        Initialise le client Spotify avec Client Credentials Flow
        (pas besoin d'authentification utilisateur pour lire une playlist publique)
        
        Args:
            client_id: Client ID de ton app Spotify
            client_secret: Client Secret de ton app Spotify
        """
        auth_manager = SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret
        )
        self.sp = spotipy.Spotify(auth_manager=auth_manager)
    
    def get_playlist_albums(self, playlist_id: str) -> List[Dict]:
        """
        Récupère tous les albums uniques d'une playlist
        
        Args:
            playlist_id: ID ou URL de la playlist Spotify (doit être publique!)
            
        Returns:
            Liste de dictionnaires avec les infos des albums
        """
        # Extraire l'ID si c'est une URL complète
        if 'spotify.com/playlist/' in playlist_id:
            playlist_id = playlist_id.split('playlist/')[-1].split('?')[0]
        
        albums = {}  # Dict pour éviter les doublons
        offset = 0
        limit = 100
        
        print(f"Récupération de la playlist {playlist_id}...")
        
        while True:
            results = self.sp.playlist_tracks(
                playlist_id,
                offset=offset,
                limit=limit,
                fields='items(track(album(id,name,artists,release_date,images,external_urls))),next'
            )
            
            if not results['items']:
                break
            
            for item in results['items']:
                if not item['track'] or not item['track']['album']:
                    continue
                
                album = item['track']['album']
                album_id = album['id']
                
                # Éviter les doublons
                if album_id not in albums:
                    albums[album_id] = {
                        'id': album_id,
                        'name': album['name'],
                        'artist': album['artists'][0]['name'] if album['artists'] else 'Unknown',
                        'release_date': album['release_date'],
                        'cover_url': album['images'][0]['url'] if album['images'] else None,
                        'spotify_url': album['external_urls']['spotify']
                    }
            
            if not results['next']:
                break
            
            offset += limit
        
        print(f"✓ {len(albums)} albums uniques trouvés")
        return list(albums.values())
    
    def get_album_top_tracks(self, album_id: str, limit: int = 5) -> List[str]:
        """
        Récupère les pistes d'un album (ordonnées par popularité si possible)
        
        Args:
            album_id: ID de l'album Spotify
            limit: Nombre maximum de tracks à retourner
            
        Returns:
            Liste des noms de tracks
        """
        try:
            results = self.sp.album_tracks(album_id, limit=50)
            tracks = results['items']
            
            # Récupérer les détails avec popularité
            track_ids = [t['id'] for t in tracks if t['id']]
            
            if track_ids:
                # Récupérer les infos complètes par batch de 50
                detailed_tracks = []
                for i in range(0, len(track_ids), 50):
                    batch = track_ids[i:i+50]
                    track_details = self.sp.tracks(batch)
                    detailed_tracks.extend(track_details['tracks'])
                
                # Trier par popularité
                detailed_tracks.sort(key=lambda x: x.get('popularity', 0), reverse=True)
                
                return [t['name'] for t in detailed_tracks[:limit]]
            else:
                # Fallback: retourner les tracks dans l'ordre de l'album
                return [t['name'] for t in tracks[:limit]]
            
        except Exception as e:
            print(f"Erreur lors de la récupération des tracks: {e}")
            return []
    
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
        
        print(f"\n🎵 Track sélectionné dans la playlist: {playlist_track_name}")
        
        # Récupérer l'album complet
        album = self.sp.album(album_id)
        
        print(f"📀 Album: {album['name']} - {album['artists'][0]['name'] if album['artists'] else 'Unknown'}")
        
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
        
        # Nettoyer le nom du track de la playlist pour la comparaison
        def clean_track_name(name):
            """Nettoie un nom de track pour comparaison"""
            import re
            name = name.lower().strip()
            # Supprimer les mentions de remaster/remix/etc
            name = re.sub(r'\s*[-\(]\s*(remaster|remix|re-master|edit|version|live|demo).*', '', name, flags=re.IGNORECASE)
            # Supprimer les espaces multiples
            name = re.sub(r'\s+', ' ', name)
            return name.strip()
        
        playlist_track_clean = clean_track_name(playlist_track_name)
        print(f"🔍 Recherche de: '{playlist_track_clean}' (nettoyé)")
        
        for t in detailed_tracks[:5]:
            track_clean = clean_track_name(t['name'])
            is_playlist_track = track_clean == playlist_track_clean
            
            tracks_with_metadata.append({
                'name': t['name'],
                'in_playlist': is_playlist_track
            })
            
            if is_playlist_track:
                print(f"✓ Track trouvé dans le top 5: {t['name']} (match avec '{playlist_track_name}')")
        
        return {
            'title': album['name'],
            'artist': album['artists'][0]['name'] if album['artists'] else 'Unknown',
            'release_date': album['release_date'],
            'cover_url': album['images'][0]['url'] if album['images'] else None,
            'tracks': tracks_with_metadata,
            'spotify_url': album['external_urls']['spotify']
        }


def setup_spotify_credentials():
    """
    Guide pour configurer les credentials Spotify
    """
    print("""
╔═══════════════════════════════════════════════════════════════╗
║          CONFIGURATION SPOTIFY API - ÉTAPE PAR ÉTAPE          ║
╚═══════════════════════════════════════════════════════════════╝

1. Va sur https://developer.spotify.com/dashboard
2. Connecte-toi avec ton compte Spotify
3. Clique sur "Create app"
4. Remplis les infos :
   - App name: "Album du jour Inky"
   - App description: "Display pour Raspberry Pi"
   - Redirect URI: http://localhost:8888/callback
   - Coche "Web API"
5. Clique sur "Save"
6. Dans la page de ton app, clique sur "Settings"
7. Note ton Client ID et Client Secret

Ensuite, crée un fichier .env avec :
    SPOTIFY_CLIENT_ID=ton_client_id
    SPOTIFY_CLIENT_SECRET=ton_client_secret
    SPOTIFY_PLAYLIST_ID=id_de_ta_playlist

IMPORTANT: Ta playlist doit être PUBLIQUE pour que ça fonctionne
sans authentification utilisateur en mode headless (SSH).

Pour trouver l'ID de ta playlist :
- Ouvre ta playlist sur Spotify
- Clique sur "..." puis "Partager" > "Copier le lien"
- L'ID est la partie après /playlist/ dans l'URL
- Exemple: spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
  → L'ID est: 37i9dQZF1DXcBWIGoYBM5M
""")


# === EXEMPLE D'UTILISATION ===
if __name__ == "__main__":
    # Charger les credentials depuis variables d'environnement ou .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("Info: python-dotenv non installé, utilisation des variables d'environnement")
    
    CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
    CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
    PLAYLIST_ID = os.getenv('SPOTIFY_PLAYLIST_ID')
    
    # Vérifier si les credentials sont configurés
    if not CLIENT_ID or not CLIENT_SECRET:
        setup_spotify_credentials()
        print("\n⚠️  Configure tes credentials Spotify d'abord!")
        exit(1)
    
    if not PLAYLIST_ID:
        print("\n⚠️  Définis SPOTIFY_PLAYLIST_ID dans ton .env ou variables d'environnement")
        exit(1)
    
    # Initialiser le fetcher
    fetcher = SpotifyAlbumFetcher(CLIENT_ID, CLIENT_SECRET)
    
    # Récupérer un album aléatoire
    album_data = fetcher.get_random_album_from_playlist(PLAYLIST_ID)
    
    if album_data:
        print("\n✓ Données récupérées avec succès!")
        print(f"  Titre: {album_data['title']}")
        print(f"  Artiste: {album_data['artist']}")
        print(f"  Date: {album_data['release_date']}")
        print(f"  Tracks: {len(album_data['tracks'])}")
        print(f"  URL: {album_data['spotify_url']}")
    else:
        print("\n✗ Impossible de récupérer l'album")

    
    def get_playlist_albums(self, playlist_id: str) -> List[Dict]:
        """
        Récupère tous les albums uniques d'une playlist
        
        Args:
            playlist_id: ID ou URL de la playlist Spotify
            
        Returns:
            Liste de dictionnaires avec les infos des albums
        """
        # Extraire l'ID si c'est une URL complète
        if 'spotify.com/playlist/' in playlist_id:
            playlist_id = playlist_id.split('playlist/')[-1].split('?')[0]
        
        albums = {}  # Dict pour éviter les doublons
        offset = 0
        limit = 100
        
        print(f"Récupération de la playlist {playlist_id}...")
        
        while True:
            results = self.sp.playlist_tracks(
                playlist_id,
                offset=offset,
                limit=limit,
                fields='items(track(album(id,name,artists,release_date,images,external_urls))),next'
            )
            
            if not results['items']:
                break
            
            for item in results['items']:
                if not item['track'] or not item['track']['album']:
                    continue
                
                album = item['track']['album']
                album_id = album['id']
                
                # Éviter les doublons
                if album_id not in albums:
                    albums[album_id] = {
                        'id': album_id,
                        'name': album['name'],
                        'artist': album['artists'][0]['name'] if album['artists'] else 'Unknown',
                        'release_date': album['release_date'],
                        'cover_url': album['images'][0]['url'] if album['images'] else None,
                        'spotify_url': album['external_urls']['spotify']
                    }
            
            if not results['next']:
                break
            
            offset += limit
        
        print(f"✓ {len(albums)} albums uniques trouvés")
        return list(albums.values())
    
    def get_album_top_tracks(self, album_id: str, limit: int = 5) -> List[str]:
        """
        Récupère les pistes d'un album (ordonnées par popularité si possible)
        
        Args:
            album_id: ID de l'album Spotify
            limit: Nombre maximum de tracks à retourner
            
        Returns:
            Liste des noms de tracks
        """
        try:
            results = self.sp.album_tracks(album_id, limit=50)
            tracks = results['items']
            
            # Récupérer les détails avec popularité
            track_ids = [t['id'] for t in tracks if t['id']]
            
            if track_ids:
                # Récupérer les infos complètes par batch de 50
                detailed_tracks = []
                for i in range(0, len(track_ids), 50):
                    batch = track_ids[i:i+50]
                    track_details = self.sp.tracks(batch)
                    detailed_tracks.extend(track_details['tracks'])
                
                # Trier par popularité
                detailed_tracks.sort(key=lambda x: x.get('popularity', 0), reverse=True)
                
                return [t['name'] for t in detailed_tracks[:limit]]
            else:
                # Fallback: retourner les tracks dans l'ordre de l'album
                return [t['name'] for t in tracks[:limit]]
            
        except Exception as e:
            print(f"Erreur lors de la récupération des tracks: {e}")
            return []
    
    def get_random_album_from_playlist(self, playlist_id: str) -> Optional[Dict]:
        """
        Sélectionne un album aléatoire depuis une playlist
        
        Args:
            playlist_id: ID ou URL de la playlist
            
        Returns:
            Dictionnaire avec toutes les infos de l'album pour create_album_display()
        """
        albums = self.get_playlist_albums(playlist_id)
        
        if not albums:
            print("Aucun album trouvé dans la playlist")
            return None
        
        # Choisir un album aléatoire
        selected = random.choice(albums)
        
        print(f"\n🎵 Album sélectionné: {selected['name']} - {selected['artist']}")
        
        # Récupérer les tracks
        tracks = self.get_album_top_tracks(selected['id'])
        
        return {
            'title': selected['name'],
            'artist': selected['artist'],
            'release_date': selected['release_date'],
            'cover_url': selected['cover_url'],
            'tracks': tracks,
            'spotify_url': selected['spotify_url']
        }


def setup_spotify_credentials():
    """
    Guide pour configurer les credentials Spotify
    """
    print("""
╔═══════════════════════════════════════════════════════════════╗
║          CONFIGURATION SPOTIFY API - ÉTAPE PAR ÉTAPE          ║
╚═══════════════════════════════════════════════════════════════╝

1. Va sur https://developer.spotify.com/dashboard
2. Connecte-toi avec ton compte Spotify
3. Clique sur "Create app"
4. Remplis les infos :
   - App name: "Album du jour Inky"
   - App description: "Display pour Raspberry Pi"
   - Redirect URI: http://localhost:8888/callback
   - Coche "Web API"
5. Clique sur "Save"
6. Dans la page de ton app, clique sur "Settings"
7. Note ton Client ID et Client Secret

Ensuite, crée un fichier .env avec :
    SPOTIFY_CLIENT_ID=ton_client_id
    SPOTIFY_CLIENT_SECRET=ton_client_secret
    SPOTIFY_PLAYLIST_ID=id_de_ta_playlist

Pour trouver l'ID de ta playlist :
- Ouvre ta playlist sur Spotify
- Clique sur "..." puis "Partager" > "Copier le lien"
- L'ID est la partie après /playlist/ dans l'URL
- Exemple: spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
  → L'ID est: 37i9dQZF1DXcBWIGoYBM5M
""")


# === EXEMPLE D'UTILISATION ===
if __name__ == "__main__":
    # Charger les credentials depuis variables d'environnement ou .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("Info: python-dotenv non installé, utilisation des variables d'environnement")
    
    CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
    CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
    PLAYLIST_ID = os.getenv('SPOTIFY_PLAYLIST_ID')
    
    # Vérifier si les credentials sont configurés
    if not CLIENT_ID or not CLIENT_SECRET:
        setup_spotify_credentials()
        print("\n⚠️  Configure tes credentials Spotify d'abord!")
        exit(1)
    
    if not PLAYLIST_ID:
        print("\n⚠️  Définis SPOTIFY_PLAYLIST_ID dans ton .env ou variables d'environnement")
        exit(1)
    
    # Initialiser le fetcher
    fetcher = SpotifyAlbumFetcher(CLIENT_ID, CLIENT_SECRET)
    
    # Récupérer un album aléatoire
    album_data = fetcher.get_random_album_from_playlist(PLAYLIST_ID)
    
    if album_data:
        print("\n✓ Données récupérées avec succès!")
        print(f"  Titre: {album_data['title']}")
        print(f"  Artiste: {album_data['artist']}")
        print(f"  Date: {album_data['release_date']}")
        print(f"  Tracks: {len(album_data['tracks'])}")
        print(f"  URL: {album_data['spotify_url']}")
    else:
        print("\n✗ Impossible de récupérer l'album")