#!/bin/bash
# Configuration Dual Screen pour LTC Interface

echo "=== Configuration Dual Screen LTC Interface ==="
echo

# Détection des écrans connectés
echo "Détection des écrans connectés..."
xrandr --query | grep " connected"

echo
echo "Configuration recommandée:"
echo "1. Écran tactile : Interface de contrôle"
echo "2. Écran HDMI : Affichage timecode grand format"
echo

# Configuration automatique si deux écrans détectés
SCREENS=$(xrandr --query | grep " connected" | wc -l)

if [ $SCREENS -ge 2 ]; then
    echo "Deux écrans ou plus détectés. Configuration automatique..."
    
    # Récupération des noms des écrans
    SCREEN1=$(xrandr --query | grep " connected" | head -1 | cut -d' ' -f1)
    SCREEN2=$(xrandr --query | grep " connected" | head -2 | tail -1 | cut -d' ' -f1)
    
    echo "Écran principal : $SCREEN1"
    echo "Écran secondaire : $SCREEN2"
    
    # Configuration dual screen
    echo "Configuration en dual screen..."
    xrandr --output $SCREEN1 --mode 800x480 --pos 0x0 --primary
    xrandr --output $SCREEN2 --mode 1920x1080 --pos 800x0
    
    echo "✓ Configuration dual screen appliquée"
    
    # Sauvegarde de la configuration
    cat > /home/$(whoami)/.config/autostart/dual-screen-setup.desktop << EOF
[Desktop Entry]
Type=Application
Name=Dual Screen Setup
Exec=bash -c 'sleep 5 && xrandr --output $SCREEN1 --mode 800x480 --pos 0x0 --primary && xrandr --output $SCREEN2 --mode 1920x1080 --pos 800x0'
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF
    
    echo "✓ Configuration sauvegardée pour le démarrage automatique"
    
else
    echo "Un seul écran détecté. L'affichage HDMI fonctionnera en fenêtre."
fi

# Configuration du bureau étendu
echo
echo "Configuration du bureau étendu..."

# Création d'un script de démarrage pour l'interface LTC
cat > /home/$(whoami)/start_ltc_interface.sh << 'EOF'
#!/bin/bash
# Script de démarrage LTC Interface avec gestion dual screen

# Attendre que X soit prêt
sleep 3

# Vérifier les écrans
SCREENS=$(xrandr --query | grep " connected" | wc -l)

if [ $SCREENS -ge 2 ]; then
    # Configuration dual screen
    SCREEN1=$(xrandr --query | grep " connected" | head -1 | cut -d' ' -f1)
    SCREEN2=$(xrandr --query | grep " connected" | head -2 | tail -1 | cut -d' ' -f1)
    
    # Appliquer la configuration
    xrandr --output $SCREEN1 --mode 800x480 --pos 0x0 --primary
    xrandr --output $SCREEN2 --mode 1920x1080 --pos 800x0
    
    # Attendre un peu
    sleep 2
fi

# Démarrer l'interface LTC
cd /home/$(whoami)/ltc-interface
python3 ltc_interface.py

EOF

chmod +x /home/$(whoami)/start_ltc_interface.sh

# Mise à jour du lanceur desktop
cat > /home/$(whoami)/Desktop/LTC-Interface.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=LTC Interface
Comment=LTC Reader/Generator Interface avec affichage dual screen
Exec=/home/$(whoami)/start_ltc_interface.sh
Icon=applications-multimedia
Terminal=false
Categories=AudioVideo;Audio;
EOF

chmod +x /home/$(whoami)/Desktop/LTC-Interface.desktop

# Copie pour autostart
cp /home/$(whoami)/Desktop/LTC-Interface.desktop /home/$(whoami)/.config/autostart/

echo
echo "=== Instructions d'utilisation ==="
echo "1. Connectez votre écran HDMI secondaire"
echo "2. Redémarrez le Raspberry Pi"
echo "3. L'interface de contrôle apparaîtra sur l'écran tactile"
echo "4. Cliquez sur 'ACTIVER AFFICHAGE HDMI' pour afficher le timecode en grand"
echo "5. Utilisez Échap ou F11 pour basculer le plein écran sur l'affichage HDMI"
echo
echo "=== Résolutions supportées ==="
echo "Écran tactile : 800x480 (écran officiel 7\")"
echo "Écran HDMI : 1920x1080 (Full HD recommandé)"
echo
echo "Pour tester la configuration :"
echo "./start_ltc_interface.sh"
echo
echo "=== Configuration terminée ==="
