#!/usr/bin/env python3
"""
Interface LTC Reader/Generator pour Raspberry Pi
Utilise ltc-tools pour lire et générer du timecode LTC
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import time
import re
from datetime import datetime, timedelta
import signal
import os

class TimecodeDisplay:
    """Fenêtre d'affichage plein écran pour le timecode sur écran HDMI"""
    
    def __init__(self, display_number=":0.1"):
        self.display_number = display_number
        self.root = None
        self.timecode_var = None
        self.status_var = None
        self.setup_display()
    
    def setup_display(self):
        """Configure l'affichage secondaire"""
        try:
            # Création d'une nouvelle fenêtre pour le second écran
            self.root = tk.Toplevel()
            self.root.title("LTC Timecode Display")
            self.root.configure(bg='black', cursor='none')
            
            # Configuration plein écran
            self.root.attributes('-fullscreen', True)
            self.root.attributes('-topmost', True)
            
            # Tenter de positionner sur le second écran
            try:
                # Obtenir la géométrie des écrans
                self.root.geometry("1920x1080+1920+0")  # Position écran secondaire
            except:
                # Fallback si pas de second écran détecté
                self.root.geometry("800x600+100+100")
            
            # Variables pour l'affichage
            self.timecode_var = tk.StringVar(value="--:--:--:--")
            self.status_var = tk.StringVar(value="EN ATTENTE")
            
            # Frame principal
            main_frame = tk.Frame(self.root, bg='black')
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Affichage du timecode (très gros)
            timecode_label = tk.Label(
                main_frame,
                textvariable=self.timecode_var,
                font=('Courier New', 120, 'bold'),
                fg='white',
                bg='black',
                justify='center'
            )
            timecode_label.pack(expand=True)
            
            # Affichage du statut (plus petit)
            status_label = tk.Label(
                main_frame,
                textvariable=self.status_var,
                font=('Arial', 24, 'normal'),
                fg='#888888',
                bg='black',
                justify='center'
            )
            status_label.pack(side=tk.BOTTOM, pady=20)
            
            # Bind pour fermer avec Échap
            self.root.bind('<Escape>', self.toggle_fullscreen)
            self.root.bind('<F11>', self.toggle_fullscreen)
            
            # Focus sur la fenêtre
            self.root.focus_set()
            
        except Exception as e:
            print(f"Erreur lors de la création de l'affichage secondaire: {e}")
            self.root = None
    
    def update_timecode(self, timecode):
        """Met à jour l'affichage du timecode"""
        if self.root and self.timecode_var:
            try:
                self.root.after(0, lambda: self.timecode_var.set(timecode))
            except tk.TclError:
                pass  # Fenêtre fermée
    
    def update_status(self, status):
        """Met à jour l'affichage du statut"""
        if self.root and self.status_var:
            try:
                self.root.after(0, lambda: self.status_var.set(status))
            except tk.TclError:
                pass  # Fenêtre fermée
    
    def toggle_fullscreen(self, event=None):
        """Bascule le mode plein écran"""
        if self.root:
            current = self.root.attributes('-fullscreen')
            self.root.attributes('-fullscreen', not current)
    
    def close(self):
        """Ferme l'affichage secondaire"""
        if self.root:
            try:
                self.root.destroy()
            except tk.TclError:
                pass
            self.root = None

class LTCInterface:
    def __init__(self, root):
        self.root = root
        self.root.title("LTC Reader/Generator - Interface de Contrôle")
        self.root.geometry("800x600")  # Agrandie pour les nouveaux contrôles
        self.root.configure(bg='#2c3e50')
        
        # Variables
        self.ltc_reader_process = None
        self.ltc_generator_process = None
        self.is_reading = False
        self.is_generating = False
        self.is_paused = False
        self.current_timecode = "00:00:00:00"
        self.paused_timecode = None
        self.generation_start_time = None
        self.generation_start_timecode = None
        
        # Affichage secondaire
        self.timecode_display = None
        self.display_enabled = False
        
        # Style
        self.setup_styles()
        
        # Interface
        self.create_widgets()
        
        # Démarrage automatique de la lecture
        self.start_reading()
        
        # Gestion de la fermeture
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_styles(self):
        """Configure les styles pour l'interface"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Style pour les gros boutons
        style.configure('Large.TButton', 
                       font=('Arial', 14, 'bold'),
                       padding=(15, 12))
        
        # Style spécial pour les boutons de contrôle
        style.configure('Control.TButton',
                       font=('Arial', 16, 'bold'),
                       padding=(20, 15))
        
        # Style pour les labels principaux
        style.configure('Large.TLabel',
                       font=('Arial', 18, 'bold'),
                       background='#2c3e50',
                       foreground='white')
        
        # Style pour l'affichage du timecode
        style.configure('Timecode.TLabel',
                       font=('Courier', 32, 'bold'),
                       background='#1a252f',
                       foreground='#00ff00',
                       anchor='center',
                       relief='sunken',
                       borderwidth=2)
    
    def create_widgets(self):
        """Crée l'interface utilisateur"""
        
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Titre
        title_label = ttk.Label(main_frame, text="LTC Reader/Generator", 
                               style='Large.TLabel')
        title_label.pack(pady=(0, 20))
        
        # Section lecture LTC
        reader_frame = ttk.LabelFrame(main_frame, text="Lecture LTC Entrante", 
                                     padding="10")
        reader_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Affichage du timecode entrant
        self.incoming_timecode_var = tk.StringVar(value="--:--:--:--")
        self.incoming_display = ttk.Label(reader_frame, 
                                         textvariable=self.incoming_timecode_var,
                                         style='Timecode.TLabel')
        self.incoming_display.pack(fill=tk.X, pady=10)
        
        # Statut de lecture
        self.reader_status_var = tk.StringVar(value="Arrêté")
        status_label = ttk.Label(reader_frame, textvariable=self.reader_status_var)
        status_label.pack()
        
        # Section affichage HDMI
        display_frame = ttk.LabelFrame(main_frame, text="Affichage HDMI Secondaire", 
                                      padding="10")
        display_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Contrôles d'affichage
        display_controls = ttk.Frame(display_frame)
        display_controls.pack(fill=tk.X)
        
        self.display_button = ttk.Button(display_controls, text="ACTIVER AFFICHAGE HDMI", 
                                        command=self.toggle_hdmi_display,
                                        style='Large.TButton')
        self.display_button.pack(side=tk.LEFT, padx=(0, 10), expand=True, fill=tk.X)
        
        # Statut de l'affichage
        self.display_status_var = tk.StringVar(value="Désactivé")
        display_status = ttk.Label(display_controls, textvariable=self.display_status_var)
        display_status.pack(side=tk.RIGHT)
        
        # Instructions
        instructions = ttk.Label(display_frame, 
                                text="Connectez un écran HDMI secondaire pour afficher le timecode en grand format\n"
                                     "Échap ou F11 pour basculer le plein écran sur l'affichage HDMI",
                                font=('Arial', 9),
                                foreground='gray')
        instructions.pack(pady=5)
        
        # Section génération LTC
        generator_frame = ttk.LabelFrame(main_frame, text="Génération LTC Sortante", 
                                        padding="10")
        generator_frame.pack(fill=tk.BOTH, expand=True)
        
        # Boutons de mode de génération
        mode_frame = ttk.Frame(generator_frame)
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(mode_frame, text="Heure Actuelle", 
                  command=self.generate_current_time,
                  style='Large.TButton').pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        ttk.Button(mode_frame, text="Depuis Zéro", 
                  command=self.generate_from_zero,
                  style='Large.TButton').pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        # Saisie de timecode personnalisé
        custom_frame = ttk.Frame(generator_frame)
        custom_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(custom_frame, text="Timecode personnalisé (HH:MM:SS:FF):").pack(anchor=tk.W)
        
        entry_frame = ttk.Frame(custom_frame)
        entry_frame.pack(fill=tk.X, pady=5)
        
        self.custom_timecode_var = tk.StringVar(value="01:00:00:00")
        self.custom_entry = ttk.Entry(entry_frame, textvariable=self.custom_timecode_var,
                                     font=('Courier', 16))
        self.custom_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 10))
        
        ttk.Button(entry_frame, text="Générer",
                  command=self.generate_custom_timecode,
                  style='Large.TButton').pack(side=tk.RIGHT)
        
        # Boutons de contrôle lecture (plus gros et mieux organisés)
        control_frame = ttk.Frame(generator_frame)
        control_frame.pack(fill=tk.X, pady=15)
        
        # Première ligne : Contrôles de lecture
        playback_frame = ttk.Frame(control_frame)
        playback_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.pause_button = ttk.Button(playback_frame, text="⏸️ PAUSE",
                                      command=self.pause_generation,
                                      style='Control.TButton')
        self.pause_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        
        self.resume_button = ttk.Button(playback_frame, text="▶️ REPRENDRE",
                                       command=self.resume_generation,
                                       style='Control.TButton')
        self.resume_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        # Deuxième ligne : Bouton d'arrêt (plus visible)
        stop_frame = ttk.Frame(control_frame)
        stop_frame.pack(fill=tk.X)
        
        ttk.Button(stop_frame, text="⏹️ ARRÊTER GÉNÉRATION",
                  command=self.stop_generation,
                  style='Control.TButton').pack(fill=tk.X)
        
        # Statut de génération
        self.generator_status_var = tk.StringVar(value="Arrêté")
        gen_status_label = ttk.Label(generator_frame, 
                                    textvariable=self.generator_status_var)
        gen_status_label.pack()
        
        # Mise à jour initiale des boutons
        self.update_control_buttons()
    
    def toggle_hdmi_display(self):
        """Active/désactive l'affichage HDMI secondaire"""
        if not self.display_enabled:
            try:
                self.timecode_display = TimecodeDisplay()
                if self.timecode_display.root:
                    self.display_enabled = True
                    self.display_button.config(text="DÉSACTIVER AFFICHAGE HDMI")
                    self.display_status_var.set("Activé")
                    # Mise à jour initiale
                    self.timecode_display.update_timecode(self.current_timecode)
                    if self.is_reading:
                        self.timecode_display.update_status("LECTURE LTC")
                    else:
                        self.timecode_display.update_status("EN ATTENTE")
                else:
                    messagebox.showwarning("Avertissement", 
                                         "Impossible de créer l'affichage secondaire.\n"
                                         "Vérifiez qu'un écran HDMI est connecté.")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de l'activation de l'affichage HDMI:\n{e}")
        else:
            self.close_hdmi_display()
    
    def close_hdmi_display(self):
        """Ferme l'affichage HDMI"""
        if self.timecode_display:
            self.timecode_display.close()
            self.timecode_display = None
        
        self.display_enabled = False
        self.display_button.config(text="ACTIVER AFFICHAGE HDMI")
        self.display_status_var.set("Désactivé")
    
    def update_hdmi_timecode(self, timecode):
        """Met à jour le timecode sur l'affichage HDMI"""
        if self.display_enabled and self.timecode_display:
            self.timecode_display.update_timecode(timecode)
    
    def update_hdmi_status(self, status):
        """Met à jour le statut sur l'affichage HDMI"""
        if self.display_enabled and self.timecode_display:
            self.timecode_display.update_status(status)
    
    def update_control_buttons(self):
        """Met à jour l'état des boutons de contrôle"""
        if not self.is_generating and not self.is_paused:
            # Arrêté
            self.pause_button.config(state='disabled')
            self.resume_button.config(state='disabled')
        elif self.is_generating and not self.is_paused:
            # En cours
            self.pause_button.config(state='normal')
            self.resume_button.config(state='disabled')
        elif self.is_paused:
            # En pause
            self.pause_button.config(state='disabled')
            self.resume_button.config(state='normal')
    
    def pause_generation(self):
        """Met en pause la génération LTC"""
        if self.is_generating and not self.is_paused:
            # Calculer le timecode actuel
            if self.generation_start_time and self.generation_start_timecode:
                elapsed = time.time() - self.generation_start_time
                self.paused_timecode = self.calculate_current_timecode(
                    self.generation_start_timecode, elapsed)
            
            # Arrêter le processus
            if self.ltc_generator_process:
                self.ltc_generator_process.terminate()
                self.ltc_generator_process = None
            
            self.is_generating = False
            self.is_paused = True
            self.generator_status_var.set(f"En pause : {self.paused_timecode}")
            self.update_hdmi_status(f"PAUSE: {self.paused_timecode}")
            self.update_control_buttons()
    
    def resume_generation(self):
        """Reprend la génération LTC depuis la pause"""
        if self.is_paused and self.paused_timecode:
            self.start_generation(self.paused_timecode)
            self.is_paused = False
            self.generator_status_var.set(f"Reprise depuis {self.paused_timecode}")
            self.update_hdmi_status(f"REPRISE: {self.paused_timecode}")
            self.update_control_buttons()
    
    def calculate_current_timecode(self, start_timecode, elapsed_seconds):
        """Calcule le timecode actuel basé sur le début et le temps écoulé"""
        try:
            h, m, s, f = map(int, start_timecode.split(':'))
            total_frames = (h * 3600 + m * 60 + s) * 25 + f
            
            # Ajouter les frames écoulées
            elapsed_frames = int(elapsed_seconds * 25)
            total_frames += elapsed_frames
            
            # Reconvertir en timecode
            frames = total_frames % 25
            seconds = (total_frames // 25) % 60
            minutes = (total_frames // (25 * 60)) % 60
            hours = (total_frames // (25 * 60 * 60)) % 24
            
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
        except:
            return start_timecode
    
    def validate_timecode(self, timecode):
        """Valide le format du timecode HH:MM:SS:FF"""
        pattern = r'^([0-1][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9]):([0-2][0-9])
        """Valide le format du timecode HH:MM:SS:FF"""
        pattern = r'^([0-1][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9]):([0-2][0-9])
        """Valide le format du timecode HH:MM:SS:FF"""
        pattern = r'^([0-1][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9]):([0-2][0-9])$'
        return re.match(pattern, timecode) is not None
    
    def start_reading(self):
        """Démarre la lecture du LTC entrant"""
        if self.is_reading:
            return
        
        try:
            # Commande ltcdump pour lire le LTC
            cmd = ['ltcdump', '-f', '-']
            self.ltc_reader_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            self.is_reading = True
            self.reader_status_var.set("En cours de lecture...")
            
            # Thread pour lire la sortie
            threading.Thread(target=self.read_ltc_output, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de démarrer la lecture LTC:\n{e}")
    
    def read_ltc_output(self):
        """Lit la sortie de ltcdump en continu"""
        while self.is_reading and self.ltc_reader_process:
            try:
                line = self.ltc_reader_process.stdout.readline()
                if line:
                    # Extrait le timecode de la ligne (format peut varier)
                    timecode_match = re.search(r'(\d{2}:\d{2}:\d{2}:\d{2})', line)
                    if timecode_match:
                        timecode = timecode_match.group(1)
                        self.current_timecode = timecode
                        # Mise à jour interface principale
                        self.root.after(0, lambda tc=timecode: self.incoming_timecode_var.set(tc))
                        self.root.after(0, lambda: self.reader_status_var.set("Signal LTC détecté"))
                        # Mise à jour affichage HDMI
                        self.root.after(0, lambda tc=timecode: self.update_hdmi_timecode(tc))
                        self.root.after(0, lambda: self.update_hdmi_status("LECTURE LTC"))
                else:
                    time.sleep(0.1)
            except Exception as e:
                self.root.after(0, lambda: self.reader_status_var.set("Pas de signal LTC"))
                self.root.after(0, lambda: self.update_hdmi_status("PAS DE SIGNAL"))
                time.sleep(1)
    
    def stop_reading(self):
        """Arrête la lecture du LTC"""
        self.is_reading = False
        if self.ltc_reader_process:
            self.ltc_reader_process.terminate()
            self.ltc_reader_process = None
        self.reader_status_var.set("Arrêté")
    
    def generate_current_time(self):
        """Génère un LTC avec l'heure actuelle"""
        current_time = datetime.now()
        timecode = current_time.strftime("%H:%M:%S:00")
        self.start_generation(timecode)
    
    def generate_from_zero(self):
        """Génère un LTC à partir de zéro"""
        self.start_generation("00:00:00:00")
    
    def generate_custom_timecode(self):
        """Génère un LTC avec le timecode saisi"""
        timecode = self.custom_timecode_var.get()
        if not self.validate_timecode(timecode):
            messagebox.showerror("Erreur", "Format de timecode invalide!\nUtilisez HH:MM:SS:FF")
            return
        self.start_generation(timecode)
    
    def start_generation(self, start_timecode):
        """Démarre la génération LTC"""
        self.stop_generation()  # Arrête toute génération en cours
        
        try:
            # Commande ltcgen pour générer le LTC
            cmd = ['ltcgen', '-f', '25', '-s', start_timecode, '-']
            self.ltc_generator_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.is_generating = True
            self.generator_status_var.set(f"Génération depuis {start_timecode}")
            
            # Mise à jour de l'affichage HDMI pour la génération
            self.update_hdmi_status(f"GÉNÉRATION: {start_timecode}")
            
            # Démarrer la simulation du timecode généré pour l'affichage
            self.start_timecode_simulation(start_timecode)
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de démarrer la génération LTC:\n{e}")
    
    def start_timecode_simulation(self, start_timecode):
        """Simule l'affichage du timecode généré"""
        if not self.is_generating:
            return
        
        def simulate_timecode():
            current = start_timecode
            while self.is_generating:
                try:
                    # Convertir en secondes
                    h, m, s, f = map(int, current.split(':'))
                    total_frames = (h * 3600 + m * 60 + s) * 25 + f
                    
                    # Incrémenter d'une frame
                    total_frames += 1
                    
                    # Reconvertir
                    frames = total_frames % 25
                    seconds = (total_frames // 25) % 60
                    minutes = (total_frames // (25 * 60)) % 60
                    hours = (total_frames // (25 * 60 * 60)) % 24
                    
                    current = f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
                    
                    # Mise à jour de l'affichage HDMI
                    if self.display_enabled:
                        self.root.after(0, lambda tc=current: self.update_hdmi_timecode(tc))
                    
                    time.sleep(1/25)  # 25 fps
                    
                except Exception:
                    break
        
        # Lancer la simulation dans un thread séparé
        threading.Thread(target=simulate_timecode, daemon=True).start()
    
    def stop_generation(self):
        """Arrête la génération LTC"""
        self.is_generating = False
        if self.ltc_generator_process:
            self.ltc_generator_process.terminate()
            self.ltc_generator_process = None
        self.generator_status_var.set("Arrêté")
        self.update_hdmi_status("ARRÊT GÉNÉRATION")
    
    def on_closing(self):
        """Nettoyage avant fermeture"""
        self.stop_reading()
        self.stop_generation()
        self.close_hdmi_display()
        self.root.destroy()

def check_ltc_tools():
    """Vérifie que ltc-tools est installé"""
    try:
        subprocess.run(['ltcdump', '--help'], capture_output=True)
        subprocess.run(['ltcgen', '--help'], capture_output=True)
        return True
    except FileNotFoundError:
        return False

def main():
    """Fonction principale"""
    # Vérification des outils LTC
    if not check_ltc_tools():
        print("Erreur: ltc-tools n'est pas installé!")
        print("Installez-le avec: sudo apt-get install ltc-tools")
        return
    
    # Création de l'interface
    root = tk.Tk()
    app = LTCInterface(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.on_closing()

if __name__ == "__main__":
    main()

        return re.match(pattern, timecode) is not None
        """Valide le format du timecode HH:MM:SS:FF"""
        pattern = r'^([0-1][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9]):([0-2][0-9])$'
        return re.match(pattern, timecode) is not None
    
    def start_reading(self):
        """Démarre la lecture du LTC entrant"""
        if self.is_reading:
            return
        
        try:
            # Commande ltcdump pour lire le LTC
            cmd = ['ltcdump', '-f', '-']
            self.ltc_reader_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            self.is_reading = True
            self.reader_status_var.set("En cours de lecture...")
            
            # Thread pour lire la sortie
            threading.Thread(target=self.read_ltc_output, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de démarrer la lecture LTC:\n{e}")
    
    def read_ltc_output(self):
        """Lit la sortie de ltcdump en continu"""
        while self.is_reading and self.ltc_reader_process:
            try:
                line = self.ltc_reader_process.stdout.readline()
                if line:
                    # Extrait le timecode de la ligne (format peut varier)
                    timecode_match = re.search(r'(\d{2}:\d{2}:\d{2}:\d{2})', line)
                    if timecode_match:
                        timecode = timecode_match.group(1)
                        self.current_timecode = timecode
                        # Mise à jour interface principale
                        self.root.after(0, lambda tc=timecode: self.incoming_timecode_var.set(tc))
                        self.root.after(0, lambda: self.reader_status_var.set("Signal LTC détecté"))
                        # Mise à jour affichage HDMI
                        self.root.after(0, lambda tc=timecode: self.update_hdmi_timecode(tc))
                        self.root.after(0, lambda: self.update_hdmi_status("LECTURE LTC"))
                else:
                    time.sleep(0.1)
            except Exception as e:
                self.root.after(0, lambda: self.reader_status_var.set("Pas de signal LTC"))
                self.root.after(0, lambda: self.update_hdmi_status("PAS DE SIGNAL"))
                time.sleep(1)
    
    def stop_reading(self):
        """Arrête la lecture du LTC"""
        self.is_reading = False
        if self.ltc_reader_process:
            self.ltc_reader_process.terminate()
            self.ltc_reader_process = None
        self.reader_status_var.set("Arrêté")
    
    def generate_current_time(self):
        """Génère un LTC avec l'heure actuelle"""
        current_time = datetime.now()
        timecode = current_time.strftime("%H:%M:%S:00")
        self.start_generation(timecode)
    
    def generate_from_zero(self):
        """Génère un LTC à partir de zéro"""
        self.start_generation("00:00:00:00")
    
    def generate_custom_timecode(self):
        """Génère un LTC avec le timecode saisi"""
        timecode = self.custom_timecode_var.get()
        if not self.validate_timecode(timecode):
            messagebox.showerror("Erreur", "Format de timecode invalide!\nUtilisez HH:MM:SS:FF")
            return
        self.start_generation(timecode)
    
    def start_generation(self, start_timecode):
        """Démarre la génération LTC"""
        self.stop_generation()  # Arrête toute génération en cours
        
        try:
            # Commande ltcgen pour générer le LTC
            cmd = ['ltcgen', '-f', '25', '-s', start_timecode, '-']
            self.ltc_generator_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.is_generating = True
            self.generator_status_var.set(f"Génération depuis {start_timecode}")
            
            # Mise à jour de l'affichage HDMI pour la génération
            self.update_hdmi_status(f"GÉNÉRATION: {start_timecode}")
            
            # Démarrer la simulation du timecode généré pour l'affichage
            self.start_timecode_simulation(start_timecode)
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de démarrer la génération LTC:\n{e}")
    
    def start_timecode_simulation(self, start_timecode):
        """Simule l'affichage du timecode généré"""
        if not self.is_generating:
            return
        
        def simulate_timecode():
            current = start_timecode
            while self.is_generating:
                try:
                    # Convertir en secondes
                    h, m, s, f = map(int, current.split(':'))
                    total_frames = (h * 3600 + m * 60 + s) * 25 + f
                    
                    # Incrémenter d'une frame
                    total_frames += 1
                    
                    # Reconvertir
                    frames = total_frames % 25
                    seconds = (total_frames // 25) % 60
                    minutes = (total_frames // (25 * 60)) % 60
                    hours = (total_frames // (25 * 60 * 60)) % 24
                    
                    current = f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
                    
                    # Mise à jour de l'affichage HDMI
                    if self.display_enabled:
                        self.root.after(0, lambda tc=current: self.update_hdmi_timecode(tc))
                    
                    time.sleep(1/25)  # 25 fps
                    
                except Exception:
                    break
        
        # Lancer la simulation dans un thread séparé
        threading.Thread(target=simulate_timecode, daemon=True).start()
    
    def stop_generation(self):
        """Arrête la génération LTC"""
        self.is_generating = False
        if self.ltc_generator_process:
            self.ltc_generator_process.terminate()
            self.ltc_generator_process = None
        self.generator_status_var.set("Arrêté")
        self.update_hdmi_status("ARRÊT GÉNÉRATION")
    
    def on_closing(self):
        """Nettoyage avant fermeture"""
        self.stop_reading()
        self.stop_generation()
        self.close_hdmi_display()
        self.root.destroy()

def check_ltc_tools():
    """Vérifie que ltc-tools est installé"""
    try:
        subprocess.run(['ltcdump', '--help'], capture_output=True)
        subprocess.run(['ltcgen', '--help'], capture_output=True)
        return True
    except FileNotFoundError:
        return False

def main():
    """Fonction principale"""
    # Vérification des outils LTC
    if not check_ltc_tools():
        print("Erreur: ltc-tools n'est pas installé!")
        print("Installez-le avec: sudo apt-get install ltc-tools")
        return
    
    # Création de l'interface
    root = tk.Tk()
    app = LTCInterface(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.on_closing()

if __name__ == "__main__":
    main()

        return re.match(pattern, timecode) is not None
        """Valide le format du timecode HH:MM:SS:FF"""
        pattern = r'^([0-1][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9]):([0-2][0-9])
        """Valide le format du timecode HH:MM:SS:FF"""
        pattern = r'^([0-1][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9]):([0-2][0-9])$'
        return re.match(pattern, timecode) is not None
    
    def start_reading(self):
        """Démarre la lecture du LTC entrant"""
        if self.is_reading:
            return
        
        try:
            # Commande ltcdump pour lire le LTC
            cmd = ['ltcdump', '-f', '-']
            self.ltc_reader_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            self.is_reading = True
            self.reader_status_var.set("En cours de lecture...")
            
            # Thread pour lire la sortie
            threading.Thread(target=self.read_ltc_output, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de démarrer la lecture LTC:\n{e}")
    
    def read_ltc_output(self):
        """Lit la sortie de ltcdump en continu"""
        while self.is_reading and self.ltc_reader_process:
            try:
                line = self.ltc_reader_process.stdout.readline()
                if line:
                    # Extrait le timecode de la ligne (format peut varier)
                    timecode_match = re.search(r'(\d{2}:\d{2}:\d{2}:\d{2})', line)
                    if timecode_match:
                        timecode = timecode_match.group(1)
                        self.current_timecode = timecode
                        # Mise à jour interface principale
                        self.root.after(0, lambda tc=timecode: self.incoming_timecode_var.set(tc))
                        self.root.after(0, lambda: self.reader_status_var.set("Signal LTC détecté"))
                        # Mise à jour affichage HDMI
                        self.root.after(0, lambda tc=timecode: self.update_hdmi_timecode(tc))
                        self.root.after(0, lambda: self.update_hdmi_status("LECTURE LTC"))
                else:
                    time.sleep(0.1)
            except Exception as e:
                self.root.after(0, lambda: self.reader_status_var.set("Pas de signal LTC"))
                self.root.after(0, lambda: self.update_hdmi_status("PAS DE SIGNAL"))
                time.sleep(1)
    
    def stop_reading(self):
        """Arrête la lecture du LTC"""
        self.is_reading = False
        if self.ltc_reader_process:
            self.ltc_reader_process.terminate()
            self.ltc_reader_process = None
        self.reader_status_var.set("Arrêté")
    
    def generate_current_time(self):
        """Génère un LTC avec l'heure actuelle"""
        current_time = datetime.now()
        timecode = current_time.strftime("%H:%M:%S:00")
        self.start_generation(timecode)
    
    def generate_from_zero(self):
        """Génère un LTC à partir de zéro"""
        self.start_generation("00:00:00:00")
    
    def generate_custom_timecode(self):
        """Génère un LTC avec le timecode saisi"""
        timecode = self.custom_timecode_var.get()
        if not self.validate_timecode(timecode):
            messagebox.showerror("Erreur", "Format de timecode invalide!\nUtilisez HH:MM:SS:FF")
            return
        self.start_generation(timecode)
    
    def start_generation(self, start_timecode):
        """Démarre la génération LTC"""
        self.stop_generation()  # Arrête toute génération en cours
        
        try:
            # Commande ltcgen pour générer le LTC
            cmd = ['ltcgen', '-f', '25', '-s', start_timecode, '-']
            self.ltc_generator_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.is_generating = True
            self.generator_status_var.set(f"Génération depuis {start_timecode}")
            
            # Mise à jour de l'affichage HDMI pour la génération
            self.update_hdmi_status(f"GÉNÉRATION: {start_timecode}")
            
            # Démarrer la simulation du timecode généré pour l'affichage
            self.start_timecode_simulation(start_timecode)
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de démarrer la génération LTC:\n{e}")
    
    def start_timecode_simulation(self, start_timecode):
        """Simule l'affichage du timecode généré"""
        if not self.is_generating:
            return
        
        def simulate_timecode():
            current = start_timecode
            while self.is_generating:
                try:
                    # Convertir en secondes
                    h, m, s, f = map(int, current.split(':'))
                    total_frames = (h * 3600 + m * 60 + s) * 25 + f
                    
                    # Incrémenter d'une frame
                    total_frames += 1
                    
                    # Reconvertir
                    frames = total_frames % 25
                    seconds = (total_frames // 25) % 60
                    minutes = (total_frames // (25 * 60)) % 60
                    hours = (total_frames // (25 * 60 * 60)) % 24
                    
                    current = f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
                    
                    # Mise à jour de l'affichage HDMI
                    if self.display_enabled:
                        self.root.after(0, lambda tc=current: self.update_hdmi_timecode(tc))
                    
                    time.sleep(1/25)  # 25 fps
                    
                except Exception:
                    break
        
        # Lancer la simulation dans un thread séparé
        threading.Thread(target=simulate_timecode, daemon=True).start()
    
    def stop_generation(self):
        """Arrête la génération LTC"""
        self.is_generating = False
        if self.ltc_generator_process:
            self.ltc_generator_process.terminate()
            self.ltc_generator_process = None
        self.generator_status_var.set("Arrêté")
        self.update_hdmi_status("ARRÊT GÉNÉRATION")
    
    def on_closing(self):
        """Nettoyage avant fermeture"""
        self.stop_reading()
        self.stop_generation()
        self.close_hdmi_display()
        self.root.destroy()

def check_ltc_tools():
    """Vérifie que ltc-tools est installé"""
    try:
        subprocess.run(['ltcdump', '--help'], capture_output=True)
        subprocess.run(['ltcgen', '--help'], capture_output=True)
        return True
    except FileNotFoundError:
        return False

def main():
    """Fonction principale"""
    # Vérification des outils LTC
    if not check_ltc_tools():
        print("Erreur: ltc-tools n'est pas installé!")
        print("Installez-le avec: sudo apt-get install ltc-tools")
        return
    
    # Création de l'interface
    root = tk.Tk()
    app = LTCInterface(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.on_closing()

if __name__ == "__main__":
    main()

        return re.match(pattern, timecode) is not None
        """Valide le format du timecode HH:MM:SS:FF"""
        pattern = r'^([0-1][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9]):([0-2][0-9])$'
        return re.match(pattern, timecode) is not None
    
    def start_reading(self):
        """Démarre la lecture du LTC entrant"""
        if self.is_reading:
            return
        
        try:
            # Commande ltcdump pour lire le LTC
            cmd = ['ltcdump', '-f', '-']
            self.ltc_reader_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            self.is_reading = True
            self.reader_status_var.set("En cours de lecture...")
            
            # Thread pour lire la sortie
            threading.Thread(target=self.read_ltc_output, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de démarrer la lecture LTC:\n{e}")
    
    def read_ltc_output(self):
        """Lit la sortie de ltcdump en continu"""
        while self.is_reading and self.ltc_reader_process:
            try:
                line = self.ltc_reader_process.stdout.readline()
                if line:
                    # Extrait le timecode de la ligne (format peut varier)
                    timecode_match = re.search(r'(\d{2}:\d{2}:\d{2}:\d{2})', line)
                    if timecode_match:
                        timecode = timecode_match.group(1)
                        self.current_timecode = timecode
                        # Mise à jour interface principale
                        self.root.after(0, lambda tc=timecode: self.incoming_timecode_var.set(tc))
                        self.root.after(0, lambda: self.reader_status_var.set("Signal LTC détecté"))
                        # Mise à jour affichage HDMI
                        self.root.after(0, lambda tc=timecode: self.update_hdmi_timecode(tc))
                        self.root.after(0, lambda: self.update_hdmi_status("LECTURE LTC"))
                else:
                    time.sleep(0.1)
            except Exception as e:
                self.root.after(0, lambda: self.reader_status_var.set("Pas de signal LTC"))
                self.root.after(0, lambda: self.update_hdmi_status("PAS DE SIGNAL"))
                time.sleep(1)
    
    def stop_reading(self):
        """Arrête la lecture du LTC"""
        self.is_reading = False
        if self.ltc_reader_process:
            self.ltc_reader_process.terminate()
            self.ltc_reader_process = None
        self.reader_status_var.set("Arrêté")
    
    def generate_current_time(self):
        """Génère un LTC avec l'heure actuelle"""
        current_time = datetime.now()
        timecode = current_time.strftime("%H:%M:%S:00")
        self.start_generation(timecode)
    
    def generate_from_zero(self):
        """Génère un LTC à partir de zéro"""
        self.start_generation("00:00:00:00")
    
    def generate_custom_timecode(self):
        """Génère un LTC avec le timecode saisi"""
        timecode = self.custom_timecode_var.get()
        if not self.validate_timecode(timecode):
            messagebox.showerror("Erreur", "Format de timecode invalide!\nUtilisez HH:MM:SS:FF")
            return
        self.start_generation(timecode)
    
    def start_generation(self, start_timecode):
        """Démarre la génération LTC"""
        self.stop_generation()  # Arrête toute génération en cours
        
        try:
            # Commande ltcgen pour générer le LTC
            cmd = ['ltcgen', '-f', '25', '-s', start_timecode, '-']
            self.ltc_generator_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.is_generating = True
            self.generator_status_var.set(f"Génération depuis {start_timecode}")
            
            # Mise à jour de l'affichage HDMI pour la génération
            self.update_hdmi_status(f"GÉNÉRATION: {start_timecode}")
            
            # Démarrer la simulation du timecode généré pour l'affichage
            self.start_timecode_simulation(start_timecode)
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de démarrer la génération LTC:\n{e}")
    
    def start_timecode_simulation(self, start_timecode):
        """Simule l'affichage du timecode généré"""
        if not self.is_generating:
            return
        
        def simulate_timecode():
            current = start_timecode
            while self.is_generating:
                try:
                    # Convertir en secondes
                    h, m, s, f = map(int, current.split(':'))
                    total_frames = (h * 3600 + m * 60 + s) * 25 + f
                    
                    # Incrémenter d'une frame
                    total_frames += 1
                    
                    # Reconvertir
                    frames = total_frames % 25
                    seconds = (total_frames // 25) % 60
                    minutes = (total_frames // (25 * 60)) % 60
                    hours = (total_frames // (25 * 60 * 60)) % 24
                    
                    current = f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
                    
                    # Mise à jour de l'affichage HDMI
                    if self.display_enabled:
                        self.root.after(0, lambda tc=current: self.update_hdmi_timecode(tc))
                    
                    time.sleep(1/25)  # 25 fps
                    
                except Exception:
                    break
        
        # Lancer la simulation dans un thread séparé
        threading.Thread(target=simulate_timecode, daemon=True).start()
    
    def stop_generation(self):
        """Arrête la génération LTC"""
        self.is_generating = False
        if self.ltc_generator_process:
            self.ltc_generator_process.terminate()
            self.ltc_generator_process = None
        self.generator_status_var.set("Arrêté")
        self.update_hdmi_status("ARRÊT GÉNÉRATION")
    
    def on_closing(self):
        """Nettoyage avant fermeture"""
        self.stop_reading()
        self.stop_generation()
        self.close_hdmi_display()
        self.root.destroy()

def check_ltc_tools():
    """Vérifie que ltc-tools est installé"""
    try:
        subprocess.run(['ltcdump', '--help'], capture_output=True)
        subprocess.run(['ltcgen', '--help'], capture_output=True)
        return True
    except FileNotFoundError:
        return False

def main():
    """Fonction principale"""
    # Vérification des outils LTC
    if not check_ltc_tools():
        print("Erreur: ltc-tools n'est pas installé!")
        print("Installez-le avec: sudo apt-get install ltc-tools")
        return
    
    # Création de l'interface
    root = tk.Tk()
    app = LTCInterface(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.on_closing()

if __name__ == "__main__":
    main()
