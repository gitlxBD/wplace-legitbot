from dataclasses import dataclass

# Color gradient system - Green fade
class Color:
    RESET = '\033[0m'
    GREEN_LIGHT = '\033[92m'
    GREEN = '\033[32m'
    GREEN_DARK = '\033[38;5;22m'
    CYAN = '\033[96m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'

def fade(text):
    """Apply diagonal green fade effect with reflection nuances"""
    colors = [
        '\033[38;5;46m',   # Bright green
        '\033[38;5;47m',   # Bright green 2
        '\033[38;5;40m',   # Light green
        '\033[38;5;34m',   # Medium green
        '\033[38;5;28m',   # Green
        '\033[38;5;22m',   # Dark green
        '\033[38;5;28m',   # Green (reflection)
        '\033[38;5;34m',   # Medium green (reflection)
    ]
    lines = text.split('\n')
    result = []
    total_chars = sum(len(line) for line in lines)
    char_count = 0
    
    for line_num, line in enumerate(lines):
        line_result = ""
        for i, char in enumerate(line):
            # Position diagonale avec espacement plus large
            diagonal_pos = (line_num * 3 + i) // 4
            color_index = diagonal_pos % len(colors)
            line_result += colors[color_index] + char
            char_count += 1
        result.append(line_result)
    return '\n'.join(result) + Color.RESET

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
        print(f"\n{fade('=== Canvas area configuration ===')}")
        print(f"{Color.CYAN}Move your mouse to the TOP-LEFT corner of the canvas{Color.RESET}")
        print(f"{Color.YELLOW}Press F when ready...{Color.RESET}")
        keyboard.wait('f')
        time.sleep(0.5)
        self.config.canvas_top_left_x, self.config.canvas_top_left_y = pyautogui.position()
        print(f"{Color.GREEN}✓ Top-left: ({self.config.canvas_top_left_x}, {self.config.canvas_top_left_y}){Color.RESET}")
        print(f"\n{Color.CYAN}Move your mouse to the BOTTOM-RIGHT corner of the canvas{Color.RESET}")
        print(f"{Color.YELLOW}Press F when ready...{Color.RESET}")
        keyboard.wait('f')
        time.sleep(0.5)
        bottom_right_x, bottom_right_y = pyautogui.position()
        self.config.canvas_width = bottom_right_x - self.config.canvas_top_left_x
        self.config.canvas_height = bottom_right_y - self.config.canvas_top_left_y
        print(f"{Color.GREEN}✓ Bottom-right: ({bottom_right_x}, {bottom_right_y}){Color.RESET}")
        print(f"{Color.GREEN}✓ Size: {self.config.canvas_width}x{self.config.canvas_height}{Color.RESET}")
        grid_width = int(self.config.canvas_width / self.config.pixel_size)
        grid_height = int(self.config.canvas_height / self.config.pixel_size)
        print(f"{Color.GREEN}✓ Estimated grid: {grid_width}x{grid_height} wplace pixels{Color.RESET}")
        print(f"{Color.GREEN}✓ Pixel size: {self.config.pixel_size:.2f} px{Color.RESET}")
        print(f"\n{fade('Configuration done!')}\n")

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
        print(f"\n{Color.CYAN}🔍 Detecting small pixels...{Color.RESET}")
        pixel_size = self.config.pixel_size
        print(f"{Color.GRAY}Pixel size: {pixel_size:.4f} px ({452}/{11}){Color.RESET}")
        print(f"{Color.GRAY}Canvas: {self.config.canvas_width}x{self.config.canvas_height} px{Color.RESET}")
        print(f"{Color.GRAY}Unique color threshold: {self.config.min_unique_colors}{Color.RESET}")
        print(f"{Color.GRAY}Min variance: {self.config.min_color_variance}{Color.RESET}")
        small_pixels = []
        checked_count = 0
        grid_width = int(self.config.canvas_width / pixel_size)
        grid_height = int(self.config.canvas_height / pixel_size)
        print(f"{Color.GRAY}Grid: {grid_width}x{grid_height} wplace pixels{Color.RESET}")
        print(f"{Color.GRAY}Scanning grid with step {pixel_size:.4f} px...{Color.RESET}")
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
                print(f"{Color.YELLOW}  Progress: {progress}% ({len(small_pixels)} small pixels found){Color.RESET}")
                last_progress = progress
            canvas_y += pixel_size
            grid_y += 1
        print(f"{Color.GREEN}✓ {len(small_pixels)} small pixels detected ({checked_count} checked){Color.RESET}")
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
        print(f"\n{fade('=== Smart bot started (Teleport mode) ===')}")
        print(f"{Color.GREEN}CPS: {self.config.clicks_per_second} clicks/sec{Color.RESET}")
        print(f"{Color.GREEN}Delay between clicks: {self.calculate_click_delay():.3f}s{Color.RESET}")
        print(f"{Color.YELLOW}Press 'q' to stop{Color.RESET}\n")
        self.config.running = True
        click_count = 0
        last_scan = 0
        try:
            while self.config.running:
                if keyboard.is_pressed('q'):
                    print(f"\n{Color.YELLOW}⏸ Stop requested...{Color.RESET}")
                    break
                current_time = time.time()
                if current_time - last_scan > self.config.scan_interval or not self.small_pixels:
                    print(f"\n{Color.CYAN}📸 Capturing and analyzing canvas...{Color.RESET}")
                    image = self.capture_canvas()
                    self.small_pixels = self.detect_small_pixels(image)
                    last_scan = current_time
                if self.small_pixels:
                    pixel = self.small_pixels.pop(0)
                    canvas_x, canvas_y, score, grid_x, grid_y = pixel
                    print(f"{Color.CYAN}⚡ Teleporting to grid pixel ({grid_x},{grid_y}), score: {score:.1f}{Color.RESET}")
                    click_start = time.time()
                    self.click_at_canvas_position(canvas_x, canvas_y)
                    click_time = time.time() - click_start
                    click_count += 1
                    print(f"{Color.GREEN}✓ Click #{click_count} in {click_time*1000:.1f}ms - {len(self.small_pixels)} left{Color.RESET}")
                    delay = self.calculate_click_delay()
                    time.sleep(max(0, delay - click_time))
                else:
                    print(f"{Color.YELLOW}⏳ No small pixel, waiting for next scan...{Color.RESET}")
                    time.sleep(2)
        except KeyboardInterrupt:
            print(f"\n{Color.YELLOW}⏸ Keyboard interrupt{Color.RESET}")
        except Exception as e:
            print(f"\n{Color.RED}❌ Error: {e}{Color.RESET}")
            import traceback
            traceback.print_exc()
        finally:
            self.config.running = False
            print(f"\n{fade('=== Bot stopped ===')}")
            print(f"{Color.GREEN}Total clicks: {click_count}{Color.RESET}")
            if click_count > 0:
                print(f"{Color.GREEN}Average CPS: {self.config.clicks_per_second:.2f}{Color.RESET}")

    def test_detection(self):
        print(f"\n{Color.CYAN}📸 Capturing canvas...{Color.RESET}")
        for i in range(3, 0, -1):
            print(f"{Color.YELLOW}Starting in {i}...{Color.RESET}")
            time.sleep(1)
        image = self.capture_canvas()
        print(f"\n{Color.CYAN}🎯 Test on some positions...{Color.RESET}")
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
                status = f"{Color.YELLOW}NUANCES ⚠️{Color.RESET}" if has_nuances else f"{Color.GREEN}UNI ✓{Color.RESET}"
                grid_x = int(cx / pixel_size)
                grid_y = int(cy / pixel_size)
                pixels = region.reshape(-1, 3)
                quantized = (pixels // 15) * 15
                unique_colors = np.unique(quantized, axis=0)
                std_dev = np.std(pixels, axis=0)
                avg_std = np.mean(std_dev)
                print(f"{Color.GRAY}  Grid pixel ({grid_x},{grid_y}):{Color.RESET}")
                print(f"{Color.GRAY}    - Unique colors: {len(unique_colors)}{Color.RESET}")
                print(f"{Color.GRAY}    - Mean variance: {avg_std:.2f}{Color.RESET}")
                print(f"{Color.GRAY}    - Score: {score:.2f} - {status}{Color.RESET}")
        print(f"\n{Color.CYAN}🔍 Full detection...{Color.RESET}")
        small_pixels = self.detect_small_pixels(image)
        if small_pixels:
            print(f"\n{Color.GREEN}Top 20 nuanced pixels:{Color.RESET}")
            for i, (x, y, score, gx, gy) in enumerate(small_pixels[:20]):
                print(f"{Color.GRAY}  {i+1}. Grid ({gx},{gy}), Score: {score:.2f}{Color.RESET}")
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
        print(f"\n{Color.GREEN}💾 Images saved:{Color.RESET}")
        print(f"{Color.GRAY}  - canvas_capture.png (original image){Color.RESET}")
        print(f"{Color.GRAY}  - canvas_detection.png (with detections and grid){Color.RESET}")
        print(f"{Color.GRAY}  - Grey grid = pixels at {pixel_size:.2f}px scale{Color.RESET}")
        print(f"{Color.GRAY}  - Red circles = nuanced pixels (intensity = score){Color.RESET}")
        print(f"{Color.GRAY}  - Green numbers = top 30{Color.RESET}")

def print_logo():
    logo = r"""

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
"""
    print(fade(logo))
    print(f"{Color.RED}                by gitlxBD{Color.RESET}")
    print(f"{Color.RED}                contact: rabaisseur on Discord{Color.RESET}\n")
    
def main():
    print_logo()
    bot = WPlaceBot()
    print(f"\n{Color.GREEN}✓ Fixed pixel size: {bot.config.pixel_size:.4f} px ( ?zoom=17 ){Color.RESET}")
    print(f"{Color.GREEN}✓ Mode: Instant teleport{Color.RESET}")
    print(f"{Color.GREEN}✓ Default CPS: {bot.config.clicks_per_second} clicks/sec{Color.RESET}")
    try:
        while True:
            print(f"\n{fade('=== Main Menu ===')}")
            print(f"{Color.GREEN}1.{Color.RESET} Configure canvas area")
            print(f"{Color.GREEN}2.{Color.RESET} Test detection")
            print(f"{Color.GREEN}3.{Color.RESET} Start smart bot")
            print(f"{Color.GREEN}4.{Color.RESET} Edit parameters")
            print(f"{Color.GREEN}5.{Color.RESET} Quit")
            choice = input(f"\n{Color.CYAN}Your choice: {Color.RESET}").strip()
            if choice == '1':
                bot.configure_canvas()
            elif choice == '2':
                if bot.config.canvas_width == 1000 and bot.config.canvas_top_left_x == 0:
                    print(f"{Color.YELLOW}⚠ Please configure the canvas area first (option 1){Color.RESET}")
                else:
                    bot.test_detection()
            elif choice == '3':
                if bot.config.canvas_width == 1000 and bot.config.canvas_top_left_x == 0:
                    print(f"{Color.YELLOW}⚠ Please configure the canvas area first (option 1){Color.RESET}")
                else:
                    print(f"\n{Color.GREEN}⚡ Mode: Teleport at {bot.config.clicks_per_second} CPS{Color.RESET}")
                    print(f"{Color.YELLOW}Bot will start in 3 seconds...{Color.RESET}")
                    time.sleep(3)
                    bot.run_smart_clicker()
            elif choice == '4':
                print(f"\n{fade('=== Configuration ===')}")
                try:
                    print(f"\n{Color.CYAN}⚡ Current CPS: {bot.config.clicks_per_second} clicks/sec{Color.RESET}")
                    print(f"{Color.GRAY}   Delay between clicks: {1.0/bot.config.clicks_per_second:.3f}s{Color.RESET}")
                    cps_input = input(f"{Color.CYAN}New CPS (0.1-100) [{bot.config.clicks_per_second}]: {Color.RESET}").strip()
                    if cps_input:
                        new_cps = float(cps_input)
                        if 0.1 <= new_cps <= 100:
                            bot.config.clicks_per_second = new_cps
                            print(f"{Color.GREEN}✓ CPS set: {new_cps} clicks/s (delay: {1.0/new_cps:.3f}s){Color.RESET}")
                        else:
                            print(f"{Color.YELLOW}⚠ CPS must be between 0.1 and 100{Color.RESET}")
                    print(f"\n{Color.CYAN}Current pixel size: {bot.config.pixel_size:.4f} px{Color.RESET}")
                    custom = input(f"{Color.CYAN}Custom size? (y/n) [n]: {Color.RESET}").strip().lower()
                    if custom == 'y':
                        size = input(f"{Color.CYAN}New size [{bot.config.pixel_size:.4f}]: {Color.RESET}").strip()
                        if size:
                            bot.config.pixel_size = float(size)
                    print(f"\n{Color.CYAN}Min unique colors: {bot.config.min_unique_colors}{Color.RESET}")
                    colors = input(f"{Color.CYAN}New minimum (2-10) [{bot.config.min_unique_colors}]: {Color.RESET}").strip()
                    if colors:
                        bot.config.min_unique_colors = int(colors)
                    print(f"\n{Color.CYAN}Min variance: {bot.config.min_color_variance}{Color.RESET}")
                    variance = input(f"{Color.CYAN}New variance (5-50) [{bot.config.min_color_variance}]: {Color.RESET}").strip()
                    if variance:
                        bot.config.min_color_variance = float(variance)
                    scan = input(f"\n{Color.CYAN}Scan interval [{bot.config.scan_interval}s]: {Color.RESET}").strip()
                    if scan:
                        bot.config.scan_interval = float(scan)
                    print(f"\n{Color.GREEN}✓ Configuration updated{Color.RESET}")
                except ValueError:
                    print(f"{Color.RED}❌ Invalid values{Color.RESET}")
            elif choice == '5':
                print(f"\n{fade('Goodbye!')}")
                break
            else:
                print(f"{Color.RED}❌ Invalid choice{Color.RESET}")
    except Exception as e:
        print(f"\n{Color.RED}❌ Error: {e}{Color.RESET}")
        print(f"\n{Color.YELLOW}If this is a dependency error, install required packages with:{Color.RESET}")
        print(f"{Color.CYAN}pip install pyautogui keyboard opencv-python numpy mss{Color.RESET}")
        
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
            print(f"\n{Color.RED}❌ Missing dependencies!{Color.RESET}")
            print(f"\n{Color.YELLOW}Missing packages:{Color.RESET}")
            for package in missing_packages:
                print(f"{Color.CYAN}- {package}: {required_packages[package]}{Color.RESET}")
            print(f"\n{Color.GREEN}Install with:{Color.RESET}")
            print(f"{Color.CYAN}pip install {' '.join(missing_packages)}{Color.RESET}")
            exit(1)
        main()
    except Exception as e:
        print(f"\n{Color.RED}❌ Error: {e}{Color.RESET}")
        print(f"\n{Color.YELLOW}If this is a dependency error, install required packages with:{Color.RESET}")
        print(f"{Color.CYAN}pip install pyautogui keyboard opencv-python numpy mss{Color.RESET}")
