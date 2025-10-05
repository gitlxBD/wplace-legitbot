from dataclasses import dataclass
@dataclass
class Config:
    canvas_top_left_x: int = 0
    canvas_top_left_y: int = 0
    canvas_width: int = 1000
    canvas_height: int = 1000
    pixel_size: float = 41.07
    clicks_per_second: float = 20.0
    running: bool = False
    scan_interval: float = 10.0
    min_unique_colors: int = 4
    min_color_variance: float = 20.0

class WPlaceBot:
    def __init__(self):
        self.config = Config()
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.0
        self.small_pixels = []
        self.sct = mss.mss()

    def configure_canvas(self):
        print("\n=== Canvas area configuration ===")
        print("Move your mouse to the TOP-LEFT corner of the canvas")
        print("Press F when ready...")
        keyboard.wait('f')
        time.sleep(0.5)
        self.config.canvas_top_left_x, self.config.canvas_top_left_y = pyautogui.position()
        print(f"✓ Top-left: ({self.config.canvas_top_left_x}, {self.config.canvas_top_left_y})")
        print("\nMove your mouse to the BOTTOM-RIGHT corner of the canvas")
        print("Press F when ready...")
        keyboard.wait('f')
        time.sleep(0.5)
        bottom_right_x, bottom_right_y = pyautogui.position()
        self.config.canvas_width = bottom_right_x - self.config.canvas_top_left_x
        self.config.canvas_height = bottom_right_y - self.config.canvas_top_left_y
        print(f"✓ Bottom-right: ({bottom_right_x}, {bottom_right_y})")
        print(f"✓ Size: {self.config.canvas_width}x{self.config.canvas_height}")
        grid_width = int(self.config.canvas_width / self.config.pixel_size)
        grid_height = int(self.config.canvas_height / self.config.pixel_size)
        print(f"✓ Estimated grid: {grid_width}x{grid_height} wplace pixels")
        print(f"✓ Pixel size: {self.config.pixel_size:.2f} px")
        print("\nConfiguration done!\n")

    def capture_canvas(self):
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
        x_start = int(canvas_x)
        y_start = int(canvas_y)
        x_end = int(canvas_x + self.config.pixel_size)
        y_end = int(canvas_y + self.config.pixel_size)
        height, width = image.shape[:2]
        if x_start < 0 or y_start < 0 or x_end > width or y_end > height:
            return None
        region = image[y_start:y_end, x_start:x_end]
        return region if region.size > 0 else None

    def analyze_pixel_region(self, region):
        if region is None or region.size == 0:
            return False, 0
        height, width = region.shape[:2]
        center_y = height // 2
        center_x = width // 2
        center_color = region[center_y, center_x].astype(np.float32)
        right_x = int(center_x + (2/3) * (width - 1 - center_x))
        right_color = region[center_y, right_x].astype(np.float32)
        left_x = int(center_x - (2/3) * (center_x - 0))
        left_color = region[center_y, left_x].astype(np.float32)
        bottom_y = int(center_y + (2/3) * (height - 1 - center_y))
        bottom_color = region[bottom_y, center_x].astype(np.float32)
        top_y = int(center_y - (2/3) * (center_y - 0))
        top_color = region[top_y, center_x].astype(np.float32)
        distances = []
        distances.append(np.sqrt(np.sum((center_color - right_color) ** 2)))
        distances.append(np.sqrt(np.sum((center_color - left_color) ** 2)))
        distances.append(np.sqrt(np.sum((center_color - bottom_color) ** 2)))
        distances.append(np.sqrt(np.sum((center_color - top_color) ** 2)))
        max_distance = max(distances)
        avg_distance = np.mean(distances)
        has_nuances = max_distance > self.config.min_color_variance or avg_distance > 15
        score = max_distance + avg_distance
        return has_nuances, score

    def detect_small_pixels(self, image):
        print("\n🔍 Detecting small pixels...")
        pixel_size = self.config.pixel_size
        print(f"Pixel size: {pixel_size:.4f} px ({452}/{11})")
        print(f"Canvas: {self.config.canvas_width}x{self.config.canvas_height} px")
        print(f"Unique color threshold: {self.config.min_unique_colors}")
        print(f"Min variance: {self.config.min_color_variance}")
        small_pixels = []
        checked_count = 0
        grid_width = int(self.config.canvas_width / pixel_size)
        grid_height = int(self.config.canvas_height / pixel_size)
        print(f"Grid: {grid_width}x{grid_height} wplace pixels")
        print(f"Scanning grid with step {pixel_size:.4f} px...")
        last_progress = 0
        canvas_y = 0.0
        grid_y = 0
        while canvas_y + pixel_size <= self.config.canvas_height:
            canvas_x = 0.0
            grid_x = 0
            while canvas_x + pixel_size <= self.config.canvas_width:
                region = self.get_pixel_region_at_position(image, canvas_x, canvas_y)
                if region is not None:
                    has_nuances, score = self.analyze_pixel_region(region)
                    checked_count += 1
                    if has_nuances:
                        center_x = canvas_x + pixel_size / 2
                        center_y = canvas_y + pixel_size / 2
                        small_pixels.append((center_x, center_y, score, grid_x, grid_y))
                canvas_x += pixel_size
                grid_x += 1
            progress = int((grid_y / grid_height) * 100)
            if progress >= last_progress + 10:
                print(f"  Progress: {progress}% ({len(small_pixels)} small pixels found)")
                last_progress = progress
            canvas_y += pixel_size
            grid_y += 1
        print(f"✓ {len(small_pixels)} small pixels detected ({checked_count} checked)")
        small_pixels.sort(key=lambda x: x[2], reverse=True)
        return small_pixels

    def teleport_mouse(self, x, y):
        pyautogui.moveTo(x, y, duration=0)

    def click_instantly(self):
        pyautogui.click()

    def calculate_click_delay(self):
        return 1.0 / self.config.clicks_per_second

    def click_at_canvas_position(self, canvas_x, canvas_y):
        screen_x = self.config.canvas_top_left_x + canvas_x
        screen_y = self.config.canvas_top_left_y + canvas_y
        self.teleport_mouse(screen_x, screen_y)
        self.click_instantly()
        return True

    def run_smart_clicker(self):
        print("\n=== Smart bot started (Teleport mode) ===")
        print(f"CPS: {self.config.clicks_per_second} clicks/sec")
        print(f"Delay between clicks: {self.calculate_click_delay():.3f}s")
        print("Press 'q' to stop\n")
        self.config.running = True
        click_count = 0
        last_scan = 0
        try:
            while self.config.running:
                if keyboard.is_pressed('q'):
                    print("\n⏸ Stop requested...")
                    break
                current_time = time.time()
                if current_time - last_scan > self.config.scan_interval or not self.small_pixels:
                    print(f"\n📸 Capturing and analyzing canvas...")
                    image = self.capture_canvas()
                    self.small_pixels = self.detect_small_pixels(image)
                    last_scan = current_time
                if self.small_pixels:
                    pixel = self.small_pixels.pop(0)
                    canvas_x, canvas_y, score, grid_x, grid_y = pixel
                    print(f"⚡ Teleporting to grid pixel ({grid_x},{grid_y}), score: {score:.1f}")
                    click_start = time.time()
                    self.click_at_canvas_position(canvas_x, canvas_y)
                    click_time = time.time() - click_start
                    click_count += 1
                    print(f"✓ Click #{click_count} in {click_time*1000:.1f}ms - {len(self.small_pixels)} left")
                    delay = self.calculate_click_delay()
                    time.sleep(max(0, delay - click_time))
                else:
                    print("⏳ No small pixel, waiting for next scan...")
                    time.sleep(2)
        except KeyboardInterrupt:
            print("\n⏸ Keyboard interrupt")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.config.running = False
            print(f"\n=== Bot stopped ===")
            print(f"Total clicks: {click_count}")
            if click_count > 0:
                print(f"Average CPS: {self.config.clicks_per_second:.2f}")

    def test_detection(self):
        print("\n📸 Capturing canvas...")
        for i in range(3, 0, -1):
            print(f"Starting in {i}...")
            time.sleep(1)
        image = self.capture_canvas()
        print("\n🎯 Test on some positions...")
        pixel_size = self.config.pixel_size
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
                pixels = region.reshape(-1, 3)
                quantized = (pixels // 15) * 15
                unique_colors = np.unique(quantized, axis=0)
                std_dev = np.std(pixels, axis=0)
                avg_std = np.mean(std_dev)
                print(f"  Grid pixel ({grid_x},{grid_y}):")
                print(f"    - Unique colors: {len(unique_colors)}")
                print(f"    - Mean variance: {avg_std:.2f}")
                print(f"    - Score: {score:.2f} - {status}")
        print("\n🔍 Full detection...")
        small_pixels = self.detect_small_pixels(image)
        if small_pixels:
            print(f"\nTop 20 nuanced pixels:")
            for i, (x, y, score, gx, gy) in enumerate(small_pixels[:20]):
                print(f"  {i+1}. Grid ({gx},{gy}), Score: {score:.2f}")
        vis_image = image.copy()
        x = 0.0
        while x < self.config.canvas_width:
            cv2.line(vis_image, (int(x), 0), (int(x), self.config.canvas_height), (200, 200, 200), 1)
            x += pixel_size
        y = 0.0
        while y < self.config.canvas_height:
            cv2.line(vis_image, (0, int(y)), (self.config.canvas_width, int(y)), (200, 200, 200), 1)
            y += pixel_size
        for x, y, score, gx, gy in small_pixels:
            intensity = min(255, int(score * 20))
            color = (0, 0, intensity)
            cv2.circle(vis_image, (int(x), int(y)), 6, color, 2)
            idx = small_pixels.index((x, y, score, gx, gy))
            if idx < 30:
                cv2.putText(vis_image, f"{idx+1}",
                            (int(x)+8, int(y)+8), cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, (0, 255, 0), 2)
        cv2.imwrite('canvas_capture.png', image)
        cv2.imwrite('canvas_detection.png', vis_image)
        print(f"\n💾 Images saved:")
        print(f"  - canvas_capture.png (original image)")
        print(f"  - canvas_detection.png (with detections and grid)")
        print(f"  - Grey grid = pixels at {pixel_size:.2f}px scale")
        print(f"  - Red circles = nuanced pixels (intensity = score)")
        print(f"  - Green numbers = top 30")

def print_logo():
    print(r"""

 █     █░ ██▓███   ██▓    ▄▄▄       ▄████▄  ▓█████        ██▓    ▓█████   ▄████  ██▓▄▄▄█████▓ ▄▄▄▄    ▒█████  ▄▄▄█████▓
▓█░ █ ░█░▓██░  ██▒▓██▒   ▒████▄    ▒██▀ ▀█  ▓█   ▀       ▓██▒    ▓█   ▀  ██▒ ▀█▒▓██▒▓  ██▒ ▓▒▓█████▄ ▒██▒  ██▒▓  ██▒ ▓▒
▒█░ █ ░█ ▓██░ ██▓▒▒██░   ▒██  ▀█▄  ▒▓█    ▄ ▒███         ▒██░    ▒███   ▒██░▄▄▄░▒██▒▒ ▓██░ ▒░▒██▒ ▄██▒██░  ██▒▒ ▓██░ ▒░
░█░ █ ░█ ▒██▄█▓▒ ▒▒██░   ░██▄▄▄▄██ ▒▓▓▄ ▄██▒▒▓█  ▄       ▒██░    ▒▓█  ▄ ░▓█  ██▓░██░░ ▓██▓ ░ ▒██░█▀  ▒██   ██░░ ▓██▓ ░ 
░░██▒██▓ ▒██▒ ░  ░░██████▒▓█   ▓██▒▒ ▓███▀ ░░▒████▒      ░██████▒░▒████▒░▒▓███▀▒░██░  ▒██▒ ░ ░▓█  ▀█▓░ ████▓▒░  ▒██▒ ░ 
░ ▓░▒ ▒  ▒▓▒░ ░  ░░ ▒░▓  ░▒▒   ▓▒█░░ ░▒ ▒  ░░░ ▒░ ░      ░ ▒░▓  ░░░ ▒░ ░ ░▒   ▒ ░▓    ▒ ░░   ░▒▓███▀▒░ ▒░▒░▒░   ▒ ░░   
  ▒ ░ ░  ░▒ ░     ░ ░ ▒  ░ ▒   ▒▒ ░  ░  ▒    ░ ░  ░      ░ ░ ▒  ░ ░ ░  ░  ░   ░  ▒ ░    ░    ▒░▒   ░   ░ ▒ ▒░     ░    
  ░   ░  ░░         ░ ░    ░   ▒   ░           ░           ░ ░      ░   ░ ░   ░  ▒ ░  ░       ░    ░ ░ ░ ░ ▒    ░      
    ░                 ░  ░     ░  ░░ ░         ░  ░          ░  ░   ░  ░      ░  ░            ░          ░ ░           
                                   ░                                                               ░                   
""")
    print("                by gitlxBD")
    print("                contact: rabaisseur on Discord\n")
    
def main():
    print_logo()
    bot = WPlaceBot()
    print(f"\n✓ Fixed pixel size: {bot.config.pixel_size:.4f} px")
    print(f"✓ Mode: Instant teleport")
    print(f"✓ Default CPS: {bot.config.clicks_per_second} clicks/sec")
    try:
        while True:
            print("\n=== Main Menu ===")
            print("1. Configure canvas area")
            print("2. Test detection")
            print("3. Start smart bot")
            print("4. Edit parameters")
            print("5. Quit")
            choice = input("\nYour choice: ").strip()
            if choice == '1':
                bot.configure_canvas()
            elif choice == '2':
                if bot.config.canvas_width == 1000 and bot.config.canvas_top_left_x == 0:
                    print("⚠ Please configure the canvas area first (option 1)")
                else:
                    bot.test_detection()
            elif choice == '3':
                if bot.config.canvas_width == 1000 and bot.config.canvas_top_left_x == 0:
                    print("⚠ Please configure the canvas area first (option 1)")
                else:
                    print(f"\n⚡ Mode: Teleport at {bot.config.clicks_per_second} CPS")
                    print("Bot will start in 3 seconds...")
                    time.sleep(3)
                    bot.run_smart_clicker()
            elif choice == '4':
                print("\n=== Configuration ===")
                try:
                    print(f"\n⚡ Current CPS: {bot.config.clicks_per_second} clicks/sec")
                    print(f"   Delay between clicks: {1.0/bot.config.clicks_per_second:.3f}s")
                    cps_input = input(f"New CPS (0.1-100) [{bot.config.clicks_per_second}]: ").strip()
                    if cps_input:
                        new_cps = float(cps_input)
                        if 0.1 <= new_cps <= 100:
                            bot.config.clicks_per_second = new_cps
                            print(f"✓ CPS set: {new_cps} clicks/s (delay: {1.0/new_cps:.3f}s)")
                        else:
                            print("⚠ CPS must be between 0.1 and 100")
                    print(f"\nCurrent pixel size: {bot.config.pixel_size:.4f} px")
                    custom = input(f"Custom size? (y/n) [n]: ").strip().lower()
                    if custom == 'y':
                        size = input(f"New size [{bot.config.pixel_size:.4f}]: ").strip()
                        if size:
                            bot.config.pixel_size = float(size)
                    print(f"\nMin unique colors: {bot.config.min_unique_colors}")
                    colors = input(f"New minimum (2-10) [{bot.config.min_unique_colors}]: ").strip()
                    if colors:
                        bot.config.min_unique_colors = int(colors)
                    print(f"\nMin variance: {bot.config.min_color_variance}")
                    variance = input(f"New variance (5-50) [{bot.config.min_color_variance}]: ").strip()
                    if variance:
                        bot.config.min_color_variance = float(variance)
                    scan = input(f"\nScan interval [{bot.config.scan_interval}s]: ").strip()
                    if scan:
                        bot.config.scan_interval = float(scan)
                    print(f"\n✓ Configuration updated")
                except ValueError:
                    print("❌ Invalid values")
            elif choice == '5':
                print("\nGoodbye!")
                break
            else:
                print("❌ Invalid choice")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nIf this is a dependency error, install required packages with:")
        print("pip install pyautogui keyboard opencv-python numpy mss")
        
if __name__ == "__main__":
    try:
        required_packages = {
            'pyautogui': 'Mouse control and screen interaction',
            'keyboard': 'Keyboard monitoring and hotkeys',
            'opencv-python': 'Image processing (cv2)',
            'numpy': 'Numerical computations',
            'mss': 'Fast screen capture',
        }
        missing_packages = []
        try:
            import pyautogui
            import keyboard
            import cv2
            import numpy as np
            import mss
            import time 
        except ImportError as e:
            package = str(e).split("'")[1]
            if package in required_packages:
                missing_packages.append(package)
        if missing_packages:
            print("\n❌ Missing dependencies!")
            print("\nMissing packages:")
            for package in missing_packages:
                print(f"- {package}: {required_packages[package]}")
            print("\nInstall with:")
            print("pip install " + " ".join(missing_packages))
            exit(1)
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nIf this is a dependency error, install required packages with:")
        print("pip install pyautogui keyboard opencv-python numpy mss time")