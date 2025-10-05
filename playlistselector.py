#!/usr/bin/env python3
"""
Gestionnaire de playlists - Change la playlist utilisée pour l'album du jour
"""

import os
import sys
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


class PlaylistManager:
    """Gère les playlists Spotify"""
    
    def __init__(self, client_id: str, client_secret: str):
        """Initialise le client Spotify"""
        auth_manager = SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret
        )
        self.sp = spotipy.Spotify(auth_manager=auth_manager)
    
    def get_user_playlists(self, username: str = None, limit: int = 50):
        """
        Récupère les playlists d'un utilisateur
        
        Args:
            username: Nom d'utilisateur Spotify (optionnel si tu veux tes propres playlists)
            limit: Nombre max de playlists à récupérer
        
        Returns:
            Liste de dictionnaires avec id, nom, nombre de tracks
        """
        playlists = []
        offset = 0
        
        while True:
            if username:
                results = self.sp.user_playlists(username, limit=50, offset=offset)
            else:
                # Récupère les playlists de l'utilisateur connecté (nécessite authentification OAuth)
                print("⚠️  Pour lister tes playlists privées, il faut ton username Spotify")
                print("    Tu peux le trouver dans ton profil Spotify")
                return []
            
            if not results['items']:
                break
            
            for playlist in results['items']:
                if playlist:  # Parfois des playlists peuvent être None
                    playlists.append({
                        'id': playlist['id'],
                        'name': playlist['name'],
                        'tracks': playlist['tracks']['total'],
                        'public': playlist['public'],
                        'owner': playlist['owner']['display_name'],
                        'url': playlist['external_urls']['spotify']
                    })
            
            if not results['next'] or len(playlists) >= limit:
                break
            
            offset += 50
        
        return playlists
    
    def search_playlists(self, query: str, limit: int = 20):
        """
        Recherche des playlists publiques par nom
        
        Args:
            query: Terme de recherche
            limit: Nombre max de résultats
        
        Returns:
            Liste de playlists correspondantes
        """
        results = self.sp.search(q=query, type='playlist', limit=limit)
        
        playlists = []
        for playlist in results['playlists']['items']:
            if playlist:
                playlists.append({
                    'id': playlist['id'],
                    'name': playlist['name'],
                    'tracks': playlist['tracks']['total'],
                    'public': playlist.get('public', True),
                    'owner': playlist['owner']['display_name'],
                    'url': playlist['external_urls']['spotify']
                })
        
        return playlists
    
    def get_playlist_info(self, playlist_id: str):
        """Récupère les infos d'une playlist spécifique"""
        # Extraire l'ID si c'est une URL
        if 'spotify.com/playlist/' in playlist_id:
            playlist_id = playlist_id.split('playlist/')[-1].split('?')[0]
        
        playlist = self.sp.playlist(playlist_id)
        
        return {
            'id': playlist['id'],
            'name': playlist['name'],
            'tracks': playlist['tracks']['total'],
            'public': playlist.get('public', True),
            'owner': playlist['owner']['display_name'],
            'url': playlist['external_urls']['spotify'],
            'description': playlist.get('description', '')
        }


def update_env_file(playlist_id: str, env_path: str = '.env'):
    """
    Met à jour le fichier .env avec le nouvel ID de playlist
    
    Args:
        playlist_id: Nouvel ID de playlist
        env_path: Chemin vers le fichier .env
    """
    # Lire le fichier .env actuel
    env_lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            env_lines = f.readlines()
    
    # Mettre à jour ou ajouter SPOTIFY_PLAYLIST_ID
    updated = False
    for i, line in enumerate(env_lines):
        if line.startswith('SPOTIFY_PLAYLIST_ID='):
            env_lines[i] = f'SPOTIFY_PLAYLIST_ID={playlist_id}\n'
            updated = True
            break
    
    if not updated:
        env_lines.append(f'SPOTIFY_PLAYLIST_ID={playlist_id}\n')
    
    # Écrire le fichier .env
    with open(env_path, 'w') as f:
        f.writelines(env_lines)
    
    print(f"✓ Fichier .env mis à jour avec la playlist: {playlist_id}")


def display_playlists(playlists):
    """Affiche une liste de playlists de manière formatée"""
    if not playlists:
        print("\nAucune playlist trouvée.")
        return
    
    print(f"\n{'#':<4} {'Nom':<50} {'Tracks':<8} {'Propriétaire':<20}")
    print("=" * 85)
    
    for i, pl in enumerate(playlists, 1):
        name = pl['name'][:47] + '...' if len(pl['name']) > 50 else pl['name']
        owner = pl['owner'][:17] + '...' if len(pl['owner']) > 20 else pl['owner']
        tracks = pl['tracks']
        
        print(f"{i:<4} {name:<50} {tracks:<8} {owner:<20}")
    
    print()


def main():
    """Interface interactive pour gérer les playlists"""
    
    print("=" * 70)
    print("  🎵 GESTIONNAIRE DE PLAYLISTS - Album du jour")
    print("=" * 70)
    
    # Charger .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
    CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
    CURRENT_PLAYLIST_ID = os.getenv('SPOTIFY_PLAYLIST_ID')
    
    if not CLIENT_ID or not CLIENT_SECRET:
        print("\n❌ SPOTIFY_CLIENT_ID et SPOTIFY_CLIENT_SECRET requis!")
        print("   Configure ton .env d'abord\n")
        sys.exit(1)
    
    manager = PlaylistManager(CLIENT_ID, CLIENT_SECRET)
    
    # Afficher la playlist actuelle
    if CURRENT_PLAYLIST_ID:
        try:
            current = manager.get_playlist_info(CURRENT_PLAYLIST_ID)
            print(f"\n📀 Playlist actuelle: {current['name']}")
            print(f"   Tracks: {current['tracks']} | Propriétaire: {current['owner']}")
        except Exception as e:
            print(f"\n⚠️  Impossible de récupérer la playlist actuelle: {e}")
    else:
        print("\n⚠️  Aucune playlist configurée dans le .env")
    
    print("\n" + "=" * 70)
    print("\nOptions:")
    print("  1. Rechercher une playlist par nom")
    print("  2. Lister les playlists d'un utilisateur")
    print("  3. Utiliser une playlist à partir de son URL/ID")
    print("  4. Quitter")
    
    choice = input("\nTon choix (1-4): ").strip()
    
    if choice == '1':
        # Recherche par nom
        query = input("\nRecherche (nom de playlist): ").strip()
        if not query:
            print("❌ Recherche vide")
            return
        
        print(f"\n🔍 Recherche de '{query}'...")
        playlists = manager.search_playlists(query, limit=20)
        
        if not playlists:
            print("Aucune playlist trouvée")
            return
        
        display_playlists(playlists)
        
        selection = input("Numéro de la playlist à utiliser (ou 'q' pour annuler): ").strip()
        
        if selection.lower() == 'q':
            print("Annulé")
            return
        
        try:
            idx = int(selection) - 1
            if 0 <= idx < len(playlists):
                selected = playlists[idx]
                update_env_file(selected['id'])
                print(f"\n✓ Playlist sélectionnée: {selected['name']}")
                print(f"  URL: {selected['url']}")
            else:
                print("❌ Numéro invalide")
        except ValueError:
            print("❌ Entrée invalide")
    
    elif choice == '2':
        # Lister les playlists d'un utilisateur
        username = input("\nNom d'utilisateur Spotify: ").strip()
        if not username:
            print("❌ Nom d'utilisateur vide")
            return
        
        print(f"\n🔍 Récupération des playlists de {username}...")
        playlists = manager.get_user_playlists(username, limit=50)
        
        if not playlists:
            print("Aucune playlist trouvée")
            return
        
        display_playlists(playlists)
        
        selection = input("Numéro de la playlist à utiliser (ou 'q' pour annuler): ").strip()
        
        if selection.lower() == 'q':
            print("Annulé")
            return
        
        try:
            idx = int(selection) - 1
            if 0 <= idx < len(playlists):
                selected = playlists[idx]
                
                # Vérifier si la playlist est publique
                if not selected['public']:
                    print(f"\n⚠️  ATTENTION: Cette playlist est PRIVÉE")
                    print("   Elle ne fonctionnera que si c'est ta propre playlist")
                    confirm = input("   Continuer quand même? (o/n): ").strip().lower()
                    if confirm != 'o':
                        print("Annulé")
                        return
                
                update_env_file(selected['id'])
                print(f"\n✓ Playlist sélectionnée: {selected['name']}")
                print(f"  URL: {selected['url']}")
            else:
                print("❌ Numéro invalide")
        except ValueError:
            print("❌ Entrée invalide")
    
    elif choice == '3':
        # URL/ID directe
        playlist_input = input("\nURL ou ID de la playlist: ").strip()
        if not playlist_input:
            print("❌ Entrée vide")
            return
        
        try:
            # Vérifier la playlist
            info = manager.get_playlist_info(playlist_input)
            
            print(f"\n📀 Playlist trouvée:")
            print(f"   Nom: {info['name']}")
            print(f"   Tracks: {info['tracks']}")
            print(f"   Propriétaire: {info['owner']}")
            print(f"   Public: {'Oui' if info['public'] else 'Non'}")
            
            if not info['public']:
                print(f"\n⚠️  ATTENTION: Cette playlist est PRIVÉE")
                print("   Elle ne fonctionnera que si c'est ta propre playlist")
            
            confirm = input("\nUtiliser cette playlist? (o/n): ").strip().lower()
            
            if confirm == 'o':
                update_env_file(info['id'])
                print(f"\n✓ Playlist configurée!")
            else:
                print("Annulé")
        
        except Exception as e:
            print(f"\n❌ Erreur: {e}")
    
    elif choice == '4':
        print("\nÀ bientôt! 👋")
    
    else:
        print("❌ Choix invalide")
    
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interruption")
        sys.exit(0)