# Guide d'utilisation - Interface LTC Dual Screen pour Raspberry Pi

## Installation

### 1. Préparatifs
- Raspberry Pi avec Raspbian/Raspberry Pi OS
- **Écran tactile 7"** (officiel ou compatible) - Interface de contrôle
- **Écran HDMI secondaire** - Affichage timecode grand format
- Interface audio USB (recommandée) ou audio intégré
- Câbles audio appropriés

### 2. Installation automatique
```bash
# Téléchargez et exécutez le script d'installation
wget https://[votre-serveur]/install_ltc.sh
chmod +x install_ltc.sh
./install_ltc.sh

# Configuration dual screen
wget https://[votre-serveur]/dual_screen_config.sh
chmod +x dual_screen_config.sh
./dual_screen_config.sh
```

### 3. Installation manuelle
```bash
# Mise à jour du système
sudo apt-get update && sudo apt-get upgrade -y

# Installation des paquets
sudo apt-get install -y python3 python3-tk ltc-tools alsa-utils

# Téléchargement de l'interface
mkdir ~/ltc-interface
cd ~/ltc-interface
# Copiez le fichier ltc_interface.py ici
```

## Configuration Dual Screen

### Connexion des écrans
```
Raspberry Pi GPIO → Écran tactile 7" (DSI ou USB)
Raspberry Pi HDMI → Écran secondaire (TV/moniteur)
```

### Configuration automatique
Le système détecte automatiquement les deux écrans et les configure :
- **Écran tactile** : 800x480 - Interface de contrôle
- **Écran HDMI** : 1920x1080 - Affichage timecode

### Configuration manuelle
```bash
# Lister les écrans
xrandr --query

# Configuration dual screen manuelle
xrandr --output DSI-1 --mode 800x480 --pos 0x0 --primary
xrandr --output HDMI-1 --mode 1920x1080 --pos 800x0
```

### Vérification des périphériques audio
```bash
# Liste des sorties audio
aplay -l

# Liste des entrées audio
arecord -l

# Test de génération audio
speaker-test -t sine -f 1000 -l 1
```

### Configuration des niveaux
```bash
# Ouvrir le mixeur audio
alsamixer

# Ou pour une interface spécifique
alsamixer -c 1  # pour la carte 1
```

**Réglages recommandés :**
- Entrée ligne : 70-80%
- Sortie ligne : 60-70%
- Éviter la saturation (indicateurs rouge)

## Utilisation de l'Interface

### Démarrage
- L'interface démarre automatiquement au boot
- Ou manuellement : `python3 ~/ltc-interface/ltc_interface.py`

### Section "Lecture LTC Entrante"
- **Affichage** : Montre le timecode détecté en temps réel
- **Statut** : Indique si un signal LTC est présent
- La lecture démarre automatiquement au lancement

### Section "Affichage HDMI Secondaire"

#### Activation
- **Bouton "ACTIVER AFFICHAGE HDMI"** : Active l'affichage secondaire
- L'écran HDMI affiche le timecode en très gros caractères (blanc sur noir)
- **Bouton "DÉSACTIVER AFFICHAGE HDMI"** : Ferme l'affichage secondaire

#### Fonctionnalités
- **Affichage temps réel** : Timecode entrant ou généré affiché instantanément
- **Police géante** : Courier New 120pt pour une lisibilité maximale
- **Contraste optimal** : Blanc sur fond noir
- **Statut visuel** : Indication de l'état (lecture, génération, arrêt)

#### Contrôles clavier (sur l'affichage HDMI)
- **Échap** : Bascule entre plein écran et fenêtre
- **F11** : Même fonction que Échap

### Section "Génération LTC Sortante"

#### 1. Heure Actuelle
- Bouton "Heure Actuelle" : Génère un LTC synchronisé avec l'horloge système
- Utile pour synchroniser avec l'heure réelle

#### 2. Depuis Zéro
- Bouton "Depuis Zéro" : Démarre la génération à 00:00:00:00
- Pratique pour les tests ou les enregistrements

#### 3. Timecode Personnalisé
- Champ de saisie : Format HH:MM:SS:FF (ex: 01:30:15:12)
- Bouton "Générer" : Lance la génération depuis cette valeur
- Validation automatique du format

#### 4. Arrêt
- Bouton "ARRÊTER GÉNÉRATION" : Stoppe toute génération en cours

## Câblage Audio

### Configuration basique (jack 3.5mm)
```
Raspberry Pi → Équipement externe
Sortie audio → Entrée LTC de l'équipement
Entrée audio ← Sortie LTC de l'équipement
```

### Configuration professionnelle (interface USB)
```
Interface USB → XLR/Jack 6.35mm
Sortie 1 → Entrée LTC équipement
Entrée 1 ← Sortie LTC équipement
```

## Dépannage

### Pas de signal LTC détecté
1. Vérifiez les connexions audio
2. Contrôlez les niveaux d'entrée avec `alsamixer`
3. Testez l'entrée : `arecord -d 5 test.wav && aplay test.wav`
4. Ajustez le niveau source (équipement externe)

### Pas de génération LTC
1. Vérifiez les connexions de sortie
2. Contrôlez les niveaux de sortie avec `alsamixer`
3. Testez la sortie : `speaker-test -t sine -f 1000 -l 1`
4. Vérifiez que ltcgen fonctionne : `ltcgen -f 25 -s 00:00:00:00`

### Interface qui ne démarre pas
1. Vérifiez l'installation : `which ltcdump ltcgen`
2. Testez Python/Tkinter : `python3 -c "import tkinter"`
3. Regardez les erreurs : lancez depuis un terminal

### Problèmes dual screen
1. **Écran HDMI non détecté**
   ```bash
   # Forcer la détection HDMI
   sudo raspi-config # → Advanced Options → HDMI Force hotplug
   
   # Vérifier la détection
   xrandr --query
   tvservice -s
   ```

2. **Résolution incorrecte**
   ```bash
   # Éditer config.txt
   sudo nano /boot/config.txt
   
   # Ajouter pour forcer une résolution
   hdmi_force_hotplug=1
   hdmi_group=2
   hdmi_mode=82  # 1920x1080 60Hz
   ```

3. **Affichage HDMI ne s'active pas**
   - Vérifiez que l'écran HDMI est connecté avant le démarrage
   - Redémarrez l'interface : `./start_ltc_interface.sh`
   - Vérifiez les erreurs : lancez depuis un terminal

4. **Performance dégradée avec dual screen**
   ```bash
   # Augmenter la mémoire GPU
   sudo raspi-config # → Advanced Options → Memory Split → 128
   
   # Ou éditer directement
   echo "gpu_mem=128" | sudo tee -a /boot/config.txt
   ```

## Spécifications Techniques

### Formats supportés
- **Framerate** : 25 fps (PAL) par défaut
- **Format** : SMPTE LTC standard
- **Résolution** : 1/25ème de seconde

### Performance Dual Screen
- **CPU** : ~10-15% sur Raspberry Pi 3+ (vs 5-10% mono-écran)
- **Mémoire GPU** : 128Mo recommandés (vs 64Mo par défaut)
- **Résolutions supportées** :
  - Tactile : 800x480, 1024x600
  - HDMI : 1920x1080, 1680x1050, 1280x720

### Compatibilité écrans
- **Écran tactile** : Officiel 7", Waveshare, Kuman, etc.
- **Écran HDMI** : Tout écran/TV avec entrée HDMI
- **Dual setup** : Raspberry Pi 3B+ minimum recommandé

## Améliorations Possibles

### Interface dual screen avancée
- Contrôle de l'affichage HDMI depuis l'interface tactile
- Choix de la police et taille sur l'affichage HDMI
- Affichage de métadonnées additionnelles (framerate, état sync)
- Mode "confidence monitor" avec barres de niveau audio

### Améliorations techniques
- Support résolution 4K sur Pi 4
- Affichage sur plusieurs écrans HDMI
- Interface web pour contrôle distant de l'affichage
- Thèmes personnalisables (couleurs, polices)
- Mode "slave" pour synchronisation multi-unités

## Support

### Commandes utiles
```bash
# Status des processus LTC
ps aux | grep ltc

# Test manuel des outils
ltcdump --help
ltcgen --help

# Monitoring audio temps réel
pactl list sources short
pactl list sinks short
```

### Logs et debug
- Les erreurs s'affichent dans l'interface
- Pour plus de détails, lancez depuis un terminal
- Logs système : `journalctl -u ltc-interface`

### Ressources
- Documentation ltc-tools : `man ltcdump`, `man ltcgen`
- Forum Raspberry Pi : https://www.raspberrypi.org/forums/
- Documentation SMPTE LTC : Standards SMPTE 12M
