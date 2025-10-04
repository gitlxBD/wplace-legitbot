"""
Bot pour wplace avec taille de pixel fixe (452/11 pixels par côté)
Le bot scanne toute la grille à l'échelle précise de 452/11 pixels
et détecte les petits pixels en analysant le pourcentage de couleurs différentes.
Version avec téléportation de souris et CPS personnalisable.
"""

import pyautogui
import time
import random
import keyboard
import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional
import mss

@dataclass
class Config:
    """Configuration du bot"""
    canvas_top_left_x: int = 0
    canvas_top_left_y: int = 0
    canvas_width: int = 1000
    canvas_height: int = 1000
    
    # Taille fixe du pixel (452/11 pixels par côté pour le zoom standard)
    pixel_size: float = 41.09  # ≈ 41.09 pixels à l'écran
    
    # Paramètres du bot
    clicks_per_second: float = 5.0  # Nombre de clics par seconde
    running: bool = False
    scan_interval: float = 10.0
    
    # Seuil de détection (nombre de couleurs uniques)
    min_unique_colors: int = 4  # Minimum de couleurs distinctes pour être un petit pixel
    min_color_variance: float = 20.0  # Variance minimale de couleur

class WPlaceBot:
    def __init__(self):
        self.config = Config()
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.0  # Désactivé pour la téléportation
        self.small_pixels = []
        self.sct = mss.mss()
        
    def configure_canvas(self):
        """Configure la zone du canvas interactivement"""
        print("\n=== Configuration de la zone de canvas ===")
        print("Déplacez votre souris sur le COIN HAUT-GAUCHE du canvas")
        print("Appuyez sur ESPACE quand vous êtes prêt...")
        keyboard.wait('space')
        time.sleep(0.5)
        
        self.config.canvas_top_left_x, self.config.canvas_top_left_y = pyautogui.position()
        print(f"✓ Coin haut-gauche: ({self.config.canvas_top_left_x}, {self.config.canvas_top_left_y})")
        
        print("\nDéplacez votre souris sur le COIN BAS-DROIT du canvas")
        print("Appuyez sur ESPACE quand vous êtes prêt...")
        keyboard.wait('space')
        time.sleep(0.5)
        
        bottom_right_x, bottom_right_y = pyautogui.position()
        self.config.canvas_width = bottom_right_x - self.config.canvas_top_left_x
        self.config.canvas_height = bottom_right_y - self.config.canvas_top_left_y
        
        print(f"✓ Coin bas-droit: ({bottom_right_x}, {bottom_right_y})")
        print(f"✓ Dimensions: {self.config.canvas_width}x{self.config.canvas_height}")
        
        # Calculer le nombre de pixels dans la grille
        grid_width = int(self.config.canvas_width / self.config.pixel_size)
        grid_height = int(self.config.canvas_height / self.config.pixel_size)
        print(f"✓ Grille estimée: {grid_width}x{grid_height} pixels wplace")
        print(f"✓ Taille pixel: {self.config.pixel_size:.2f} pixels à l'écran")
        print("\nConfiguration terminée !\n")
    
    def capture_canvas(self):
        """Capture une image du canvas avec mss"""
        monitor = {
            "top": self.config.canvas_top_left_y,
            "left": self.config.canvas_top_left_x,
            "width": self.config.canvas_width,
            "height": self.config.canvas_height
        }
        
        screenshot = self.sct.grab(monitor)
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        
        return img
    
    def get_pixel_region_at_position(self, image, canvas_x, canvas_y):
        """
        Extrait la région d'un pixel à partir d'une position canvas
        en utilisant la taille fixe de pixel (452/11)
        
        Args:
            image: Image capturée du canvas
            canvas_x, canvas_y: Position relative au canvas (en pixels écran)
        
        Returns:
            Région de l'image (numpy array) ou None si hors limites
        """
        # Coordonnées de la région dans l'image capturée
        x_start = int(canvas_x)
        y_start = int(canvas_y)
        x_end = int(canvas_x + self.config.pixel_size)
        y_end = int(canvas_y + self.config.pixel_size)
        
        # Vérifier les limites
        height, width = image.shape[:2]
        if x_start < 0 or y_start < 0 or x_end > width or y_end > height:
            return None
        
        # Extraire la région
        region = image[y_start:y_end, x_start:x_end]
        
        return region if region.size > 0 else None
    
    def analyze_pixel_region(self, region):
        """
        Analyse une région de pixel pour détecter les nuances de couleur
        Méthode précise : compare la couleur au centre avec celle aux 2/3 vers les bords
        
        Args:
            region: Image numpy array de la région du pixel
            
        Returns:
            (a_des_nuances, score_difference)
        """
        if region is None or region.size == 0:
            return False, 0
        
        height, width = region.shape[:2]
        
        # Position du centre du pixel
        center_y = height // 2
        center_x = width // 2
        
        # Couleur au centre
        center_color = region[center_y, center_x].astype(np.float32)
        
        # Positions aux 2/3 vers chaque bord depuis le centre
        # 2/3 de la distance entre le centre et chaque bord
        
        # Vers la droite : centre + 2/3 * (droite - centre)
        right_x = int(center_x + (2/3) * (width - 1 - center_x))
        right_color = region[center_y, right_x].astype(np.float32)
        
        # Vers la gauche : centre - 2/3 * (centre - gauche)
        left_x = int(center_x - (2/3) * (center_x - 0))
        left_color = region[center_y, left_x].astype(np.float32)
        
        # Vers le bas : centre + 2/3 * (bas - centre)
        bottom_y = int(center_y + (2/3) * (height - 1 - center_y))
        bottom_color = region[bottom_y, center_x].astype(np.float32)
        
        # Vers le haut : centre - 2/3 * (centre - haut)
        top_y = int(center_y - (2/3) * (center_y - 0))
        top_color = region[top_y, center_x].astype(np.float32)
        
        # Calculer la distance euclidienne entre le centre et chaque point
        distances = []
        distances.append(np.sqrt(np.sum((center_color - right_color) ** 2)))
        distances.append(np.sqrt(np.sum((center_color - left_color) ** 2)))
        distances.append(np.sqrt(np.sum((center_color - bottom_color) ** 2)))
        distances.append(np.sqrt(np.sum((center_color - top_color) ** 2)))
        
        # Score = distance maximale trouvée
        max_distance = max(distances)
        avg_distance = np.mean(distances)
        
        # Un pixel a des nuances si la différence de couleur est significative
        # Une différence de 30 en distance RGB est perceptible
        has_nuances = max_distance > self.config.min_color_variance or avg_distance > 15
        
        # Score combiné pour le tri
        score = max_distance + avg_distance
        
        return has_nuances, score
    
    def detect_small_pixels(self, image):
        """
        Parcourt toute la grille en se déplaçant à l'échelle précise de 452/11 pixels
        et détecte les petits pixels
        """
        print("\n🔍 Détection des petits pixels...")
        
        pixel_size = self.config.pixel_size
        print(f"Taille pixel: {pixel_size:.4f} pixels à l'écran ({452}/{11})")
        print(f"Canvas: {self.config.canvas_width}x{self.config.canvas_height} px")
        print(f"Seuil couleurs uniques: {self.config.min_unique_colors}")
        print(f"Variance minimale: {self.config.min_color_variance}")
        
        small_pixels = []
        checked_count = 0
        
        # Calculer le nombre de pixels dans la grille
        grid_width = int(self.config.canvas_width / pixel_size)
        grid_height = int(self.config.canvas_height / pixel_size)
        
        print(f"Grille: {grid_width}x{grid_height} pixels wplace")
        print(f"Scan de la grille en déplacement précis de {pixel_size:.4f} px...")
        
        total_pixels = grid_width * grid_height
        last_progress = 0
        
        # Scanner en se déplaçant à l'échelle précise de 452/11 pixels
        canvas_y = 0.0
        grid_y = 0
        
        while canvas_y + pixel_size <= self.config.canvas_height:
            canvas_x = 0.0
            grid_x = 0
            
            while canvas_x + pixel_size <= self.config.canvas_width:
                # Extraire la région du pixel à cette position
                region = self.get_pixel_region_at_position(image, canvas_x, canvas_y)
                
                if region is not None:
                    has_nuances, score = self.analyze_pixel_region(region)
                    checked_count += 1
                    
                    if has_nuances:
                        # Position du centre du pixel (relative au canvas)
                        center_x = canvas_x + pixel_size / 2
                        center_y = canvas_y + pixel_size / 2
                        
                        small_pixels.append((center_x, center_y, score, grid_x, grid_y))
                
                # Avancer d'un pixel à droite (à l'échelle précise)
                canvas_x += pixel_size
                grid_x += 1
            
            # Afficher progression
            progress = int((grid_y / grid_height) * 100)
            if progress >= last_progress + 10:
                print(f"  Progression: {progress}% ({len(small_pixels)} petits pixels trouvés)")
                last_progress = progress
            
            # Avancer d'un pixel vers le bas (à l'échelle précise)
            canvas_y += pixel_size
            grid_y += 1
        
        print(f"✓ {len(small_pixels)} petits pixels détectés ({checked_count} pixels vérifiés)")
        
        # Trier par score (du plus élevé au plus bas)
        small_pixels.sort(key=lambda x: x[2], reverse=True)
        
        return small_pixels
    
    def teleport_mouse(self, x, y):
        """Téléporte la souris instantanément à la position donnée"""
        pyautogui.moveTo(x, y, duration=0)
        
    def click_instantly(self):
        """Effectue un clic instantané"""
        pyautogui.click()
        
    def calculate_click_delay(self):
        """Calcule le délai entre les clics basé sur le CPS"""
        return 1.0 / self.config.clicks_per_second
        
    def click_at_canvas_position(self, canvas_x, canvas_y):
        """Clique à une position donnée sur le canvas (téléportation)"""
        screen_x = self.config.canvas_top_left_x + canvas_x
        screen_y = self.config.canvas_top_left_y + canvas_y
        
        self.teleport_mouse(screen_x, screen_y)
        self.click_instantly()
        return True
    
    def run_smart_clicker(self):
        """Lance le bot avec détection automatique et CPS personnalisé"""
        print("\n=== Bot intelligent démarré (Mode Téléportation) ===")
        print(f"CPS: {self.config.clicks_per_second} clics/seconde")
        print(f"Délai entre clics: {self.calculate_click_delay():.3f}s")
        print("Appuyez sur 'q' pour arrêter\n")
        
        self.config.running = True
        click_count = 0
        last_scan = 0
        
        try:
            while self.config.running:
                if keyboard.is_pressed('q'):
                    print("\n⏸ Arrêt demandé...")
                    break
                
                current_time = time.time()
                
                # Scanner périodiquement
                if current_time - last_scan > self.config.scan_interval:
                    print(f"\n📸 Capture et analyse du canvas...")
                    image = self.capture_canvas()
                    
                    # Détecter les petits pixels
                    self.small_pixels = self.detect_small_pixels(image)
                    last_scan = current_time
                
                # Cliquer sur les petits pixels
                if self.small_pixels:
                    pixel = self.small_pixels.pop(0)
                    canvas_x, canvas_y, score, grid_x, grid_y = pixel
                    
                    print(f"⚡ Téléportation pixel grille ({grid_x},{grid_y}), score: {score:.1f}")
                    
                    # Timer pour mesurer le temps de clic
                    click_start = time.time()
                    self.click_at_canvas_position(canvas_x, canvas_y)
                    click_time = time.time() - click_start
                    
                    click_count += 1
                    print(f"✓ Clic #{click_count} en {click_time*1000:.1f}ms - {len(self.small_pixels)} restants")
                    
                    # Attendre le délai calculé basé sur le CPS
                    delay = self.calculate_click_delay()
                    time.sleep(max(0, delay - click_time))
                else:
                    print("⏳ Aucun petit pixel, attente du prochain scan...")
                    time.sleep(2)
                
        except KeyboardInterrupt:
            print("\n⏸ Interruption clavier")
        except Exception as e:
            print(f"\n❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.config.running = False
            print(f"\n=== Bot arrêté ===")
            print(f"Total de clics: {click_count}")
            if click_count > 0:
                print(f"CPS moyen: {self.config.clicks_per_second:.2f}")
    
    def test_detection(self):
        """Test la détection et génère une visualisation"""
        print("\n📸 Capture du canvas...")
        for i in range(3, 0, -1):
            print(f"Démarrage dans {i}...")
            time.sleep(1)
        image = self.capture_canvas()
        
        print("\n🎯 Test sur quelques positions...")
        pixel_size = self.config.pixel_size
        
        # Test sur les premiers pixels en partant du coin haut-gauche
        test_positions = [
            (0, 0),
            (pixel_size, 0),
            (pixel_size * 2, 0),
            (0, pixel_size),
            (pixel_size, pixel_size),
        ]
        
        for i, (cx, cy) in enumerate(test_positions):
            region = self.get_pixel_region_at_position(image, cx, cy)
            if region is not None:
                has_nuances, score = self.analyze_pixel_region(region)
                status = "NUANCES ⚠️" if has_nuances else "UNI ✓"
                grid_x = int(cx / pixel_size)
                grid_y = int(cy / pixel_size)
                
                # Afficher des stats détaillées pour debug
                pixels = region.reshape(-1, 3)
                quantized = (pixels // 15) * 15
                unique_colors = np.unique(quantized, axis=0)
                std_dev = np.std(pixels, axis=0)
                avg_std = np.mean(std_dev)
                
                print(f"  Pixel grille ({grid_x},{grid_y}):")
                print(f"    - Couleurs uniques: {len(unique_colors)}")
                print(f"    - Variance moyenne: {avg_std:.2f}")
                print(f"    - Score: {score:.2f} - {status}")
        
        # Détection complète
        print("\n🔍 Détection complète...")
        small_pixels = self.detect_small_pixels(image)
        
        if small_pixels:
            print(f"\nTop 20 pixels avec nuances:")
            for i, (x, y, score, gx, gy) in enumerate(small_pixels[:20]):
                print(f"  {i+1}. Grille ({gx},{gy}), Score: {score:.2f}")
        
        # Visualisation
        vis_image = image.copy()
        
        # Dessiner la grille de pixels (à l'échelle précise)
        x = 0.0
        while x < self.config.canvas_width:
            cv2.line(vis_image, (int(x), 0), (int(x), self.config.canvas_height), (200, 200, 200), 1)
            x += pixel_size
        
        y = 0.0
        while y < self.config.canvas_height:
            cv2.line(vis_image, (0, int(y)), (self.config.canvas_width, int(y)), (200, 200, 200), 1)
            y += pixel_size
        
        # Marquer les pixels avec nuances
        for x, y, score, gx, gy in small_pixels:
            # Couleur selon le score (rouge = beaucoup de nuances)
            intensity = min(255, int(score * 20))
            color = (0, 0, intensity)
            
            cv2.circle(vis_image, (int(x), int(y)), 6, color, 2)
            
            # Numéros pour les top 30
            idx = small_pixels.index((x, y, score, gx, gy))
            if idx < 30:
                cv2.putText(vis_image, f"{idx+1}", 
                           (int(x)+8, int(y)+8), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.5, (0, 255, 0), 2)
        
        cv2.imwrite('canvas_capture.png', image)
        cv2.imwrite('canvas_detection.png', vis_image)
        print(f"\n💾 Images sauvegardées:")
        print(f"  - canvas_capture.png (image originale)")
        print(f"  - canvas_detection.png (avec détections et grille)")
        print(f"  - Grille grise = pixels à l'échelle {pixel_size:.2f}px")
        print(f"  - Cercles rouges = pixels avec nuances (intensité = score)")
        print(f"  - Numéros verts = top 30")

def main():
    print("╔═══════════════════════════════════════════════╗")
    print("║  Bot wplace - Téléportation + CPS Custom     ║")
    print("║  Taille Fixe 452/11 px                        ║")
    print("╚═══════════════════════════════════════════════╝")
    
    bot = WPlaceBot()
    
    print(f"\n✓ Taille de pixel fixe: {bot.config.pixel_size:.4f} pixels à l'écran")
    print(f"  (Calculé depuis 452/11 pixels)")
    print(f"✓ Mode: Téléportation instantanée")
    print(f"✓ CPS par défaut: {bot.config.clicks_per_second} clics/seconde")
    
    while True:
        print("\n=== Menu Principal ===")
        print("1. Configurer la zone du canvas")
        print("2. Tester la détection")
        print("3. Lancer le bot intelligent")
        print("4. Modifier les paramètres")
        print("5. Quitter")
        
        choice = input("\nVotre choix: ").strip()
        
        if choice == '1':
            bot.configure_canvas()
            
        elif choice == '2':
            if bot.config.canvas_width == 1000 and bot.config.canvas_top_left_x == 0:
                print("⚠ Configurez d'abord la zone du canvas (option 1)")
            else:
                bot.test_detection()
                
        elif choice == '3':
            if bot.config.canvas_width == 1000 and bot.config.canvas_top_left_x == 0:
                print("⚠ Configurez d'abord la zone du canvas (option 1)")
            else:
                print(f"\n⚡ Mode: Téléportation à {bot.config.clicks_per_second} CPS")
                print("Le bot démarre dans 3 secondes...")
                time.sleep(3)
                bot.run_smart_clicker()
                
        elif choice == '4':
            print("\n=== Configuration ===")
            try:
                # Configuration CPS
                print(f"\n⚡ CPS actuel: {bot.config.clicks_per_second} clics/seconde")
                print(f"   Délai entre clics: {1.0/bot.config.clicks_per_second:.3f}s")
                cps_input = input(f"Nouveau CPS (0.1-100) [{bot.config.clicks_per_second}]: ").strip()
                if cps_input:
                    new_cps = float(cps_input)
                    if 0.1 <= new_cps <= 100:
                        bot.config.clicks_per_second = new_cps
                        print(f"✓ CPS configuré: {new_cps} clics/s (délai: {1.0/new_cps:.3f}s)")
                    else:
                        print("⚠ CPS doit être entre 0.1 et 100")
                
                # Configuration taille pixel
                print(f"\nTaille pixel actuelle: {bot.config.pixel_size:.4f} px")
                custom = input(f"Personnaliser la taille ? (o/n) [n]: ").strip().lower()
                if custom == 'o':
                    size = input(f"Nouvelle taille [{bot.config.pixel_size:.4f}]: ").strip()
                    if size:
                        bot.config.pixel_size = float(size)
                
                print(f"\nCouleurs uniques minimales: {bot.config.min_unique_colors}")
                colors = input(f"Nouveau minimum (2-10) [{bot.config.min_unique_colors}]: ").strip()
                if colors:
                    bot.config.min_unique_colors = int(colors)
                
                print(f"\nVariance minimale: {bot.config.min_color_variance}")
                variance = input(f"Nouvelle variance (5-50) [{bot.config.min_color_variance}]: ").strip()
                if variance:
                    bot.config.min_color_variance = float(variance)
                
                scan = input(f"\nIntervalle scan [{bot.config.scan_interval}s]: ").strip()
                if scan:
                    bot.config.scan_interval = float(scan)
                
                print(f"\n✓ Configuration mise à jour")
            except ValueError:
                print("❌ Valeurs invalides")
                
        elif choice == '5':
            print("\nAu revoir !")
            break
            
        else:
            print("❌ Choix invalide")

if __name__ == "__main__":
    try:
        import pyautogui
        import keyboard
        import cv2
        import numpy as np
        import mss
        import time
        main()
    except ImportError as e:
        print("❌ Dépendances manquantes !")
        print(f"\nErreur: {e}")
        print("\nInstallez avec:")
        print("pip install pyautogui keyboard opencv-python numpy mss")
