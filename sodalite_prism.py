#!/usr/bin/env python3
"""Sodalite Prism — neon laser-refraction arcade for ElbowOS."""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys

import pygame

W, H = 1080, 1920
FPS = 30
TITLE = "SODALITE PRISM"
HANDLE = "x.com/ElbowOS"

VOID = (6, 10, 28)
INK = (12, 22, 52)
NAVY = (18, 36, 78)
CYAN = (56, 230, 255)
TEAL = (28, 190, 210)
LIME = (150, 255, 90)
CORAL = (255, 92, 120)
GOLD = (255, 214, 96)
CREAM = (236, 248, 255)
VIOLET = (150, 110, 255)
MAG = (255, 70, 200)

ARENA = pygame.Rect(56, 168, W - 112, 1420)


class Spark:
    __slots__ = ("x", "y", "vx", "vy", "life", "col", "r")

    def __init__(self, x, y, vx, vy, life, col, r=4):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life, self.col, self.r = life, col, r


class Prism:
    def __init__(self, x, y, r, ang, spin):
        self.x, self.y, self.r, self.ang, self.spin = x, y, r, ang, spin

    def verts(self):
        return [
            (self.x + self.r * math.cos(self.ang + i * math.tau / 3),
             self.y + self.r * math.sin(self.ang + i * math.tau / 3))
            for i in range(3)
        ]

    def edges(self):
        v = self.verts()
        return [(v[i], v[(i + 1) % 3]) for i in range(3)]


class Gem:
    def __init__(self):
        self.x = random.uniform(ARENA.left + 80, ARENA.right - 80)
        self.y = random.uniform(ARENA.top + 420, ARENA.bottom - 80)
        self.vx = random.uniform(-70, 70)
        self.vy = random.uniform(-50, 50)
        self.r = random.choice((16, 20, 24))
        self.col = random.choice((GOLD, LIME, MAG, CORAL, CYAN))
        self.pulse = random.random() * math.tau


class Game:
    def __init__(self, record: bool):
        self.record = record
        self.surf = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.font_lg = pygame.font.Font(None, 58)
        self.font_md = pygame.font.Font(None, 44)
        self.font_sm = pygame.font.Font(None, 30)
        self.reset()
        self.screen = None
        if not record:
            self.screen = pygame.display.set_mode((W, H))
            pygame.display.set_caption(TITLE)

    def reset(self) -> None:
        self.t = 0.0
        self.score = 0
        self.combo = 0
        self.flash = 0.0
        self.sel = 1
        self.ex, self.ey = W * 0.5, ARENA.top + 36
        self.eang = math.pi * 0.5
        self.prisms = [
            Prism(280, 620, 92, 0.2, 0.55),
            Prism(800, 620, 92, 1.1, -0.45),
            Prism(540, 920, 110, 0.6, 0.35),
            Prism(300, 1220, 86, 2.0, -0.5),
            Prism(780, 1220, 86, 0.3, 0.6),
        ]
        self.gems = [Gem() for _ in range(6)]
        self.sparks: list[Spark] = []
        self.pops: list[tuple] = []
        self.stars = [(random.randint(0, W), random.randint(0, H), random.random()) for _ in range(110)]
        self.running = True
        self.beam: list[tuple[float, float]] = []

    def burst(self, x, y, col, n=12) -> None:
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(80, 420)
            self.sparks.append(Spark(x, y, math.cos(a) * sp, math.sin(a) * sp,
                                     random.uniform(0.2, 0.55), col, random.randint(3, 7)))

    def reflect(self, dx, dy, x1, y1, x2, y2):
        nx, ny = y2 - y1, x1 - x2
        ln = math.hypot(nx, ny) or 1
        nx, ny = nx / ln, ny / ln
        if dx * nx + dy * ny > 0:
            nx, ny = -nx, -ny
        dot = dx * nx + dy * ny
        return dx - 2 * dot * nx, dy - 2 * dot * ny

    def closest_edge(self, px, py, pr: Prism):
        best, bd = None, 1e9
        for (x1, y1), (x2, y2) in pr.edges():
            vx, vy = x2 - x1, y2 - y1
            L2 = vx * vx + vy * vy or 1
            t = max(0.0, min(1.0, ((px - x1) * vx + (py - y1) * vy) / L2))
            qx, qy = x1 + t * vx, y1 + t * vy
            d = math.hypot(px - qx, py - qy)
            if d < bd:
                bd, best = d, ((x1, y1), (x2, y2), d)
        return best

    def trace(self) -> None:
        x, y = self.ex, self.ey
        dx, dy = math.cos(self.eang), math.sin(self.eang)
        pts = [(x, y)]
        hits = set()
        for _ in range(280):
            x += dx * 14
            y += dy * 14
            if not ARENA.inflate(-8, -8).collidepoint(x, y):
                pts.append((x, y))
                break
            bounced = False
            for pr in self.prisms:
                hit = self.closest_edge(x, y, pr)
                if hit and hit[2] < 10:
                    (x1, y1), (x2, y2), _ = hit
                    dx, dy = self.reflect(dx, dy, x1, y1, x2, y2)
                    x += dx * 16
                    y += dy * 16
                    pts.append((x, y))
                    bounced = True
                    break
            if bounced:
                continue
            for i, g in enumerate(self.gems):
                if i in hits:
                    continue
                if math.hypot(x - g.x, y - g.y) < g.r + 10:
                    hits.add(i)
                    self.score += 10 + self.combo * 2
                    self.combo += 1
                    self.flash = 0.16
                    self.burst(g.x, g.y, g.col, 16)
                    self.pops.append((f"+{10 + (self.combo - 1) * 2}", g.x, g.y - 20, 0.55, g.col))
                    self.gems[i] = Gem()
            if len(pts) < 2 or math.hypot(x - pts[-1][0], y - pts[-1][1]) > 18:
                pts.append((x, y))
        self.beam = pts

    def update(self, dt: float) -> None:
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        self.eang = math.pi * 0.5 + math.sin(self.t * 0.7) * 0.55
        for i, pr in enumerate(self.prisms):
            if self.record:
                g = self.gems[i % len(self.gems)]
                want = math.atan2(g.y - pr.y, g.x - pr.x) + math.pi / 6
                err = (want - pr.ang + math.pi) % math.tau - math.pi
                pr.ang += max(-1.8, min(1.8, err * 2.2)) * dt
            else:
                pr.ang += pr.spin * dt
        for g in self.gems:
            g.x += g.vx * dt
            g.y += g.vy * dt
            g.pulse += dt * 4
            if g.x < ARENA.left + 50 or g.x > ARENA.right - 50:
                g.vx *= -1
            if g.y < ARENA.top + 280 or g.y > ARENA.bottom - 50:
                g.vy *= -1
            g.x = max(ARENA.left + 50, min(ARENA.right - 50, g.x))
            g.y = max(ARENA.top + 280, min(ARENA.bottom - 50, g.y))
        before = self.score
        self.trace()
        if self.score == before:
            self.combo = max(0, self.combo - (1 if int(self.t * 8) % 18 == 0 else 0))
        live = []
        for sp in self.sparks:
            sp.x += sp.vx * dt
            sp.y += sp.vy * dt + 90 * dt
            sp.life -= dt
            if sp.life > 0:
                live.append(sp)
        self.sparks = live[-240:]
        self.pops = [(a, x, y - 80 * dt, life - dt, c) for a, x, y, life, c in self.pops if life - dt > 0]

    def draw(self, s: pygame.Surface) -> None:
        s.fill(VOID)
        for sx, sy, tw in self.stars:
            yy = int((sy + self.t * (8 + tw * 18)) % H)
            c = 24 + int(tw * 90)
            pygame.draw.circle(s, (c // 3, c // 2, c), (sx, yy), 1 + int(tw * 2))
        pygame.draw.rect(s, INK, ARENA, border_radius=30)
        pygame.draw.rect(s, CYAN, ARENA, 3, border_radius=30)
        pygame.draw.rect(s, VIOLET, ARENA, 1, border_radius=30)
        if len(self.beam) > 1:
            pygame.draw.lines(s, (20, 80, 120), False, [(int(x), int(y)) for x, y in self.beam], 10)
            pygame.draw.lines(s, CYAN, False, [(int(x), int(y)) for x, y in self.beam], 4)
            pygame.draw.lines(s, CREAM, False, [(int(x), int(y)) for x, y in self.beam], 1)
        pygame.draw.circle(s, GOLD, (int(self.ex), int(self.ey)), 18)
        pygame.draw.circle(s, CREAM, (int(self.ex), int(self.ey)), 18, 2)
        pygame.draw.line(s, GOLD, (self.ex, self.ey),
                         (self.ex + math.cos(self.eang) * 40, self.ey + math.sin(self.eang) * 40), 4)
        for i, pr in enumerate(self.prisms):
            pts = [(int(x), int(y)) for x, y in pr.verts()]
            col = TEAL if i != self.sel else LIME
            pygame.draw.polygon(s, NAVY, pts)
            pygame.draw.polygon(s, col, pts, 4)
            pygame.draw.circle(s, col, (int(pr.x), int(pr.y)), 5)
        for g in self.gems:
            rr = int(g.r + 3 * math.sin(g.pulse))
            pygame.draw.circle(s, g.col, (int(g.x), int(g.y)), rr)
            pygame.draw.circle(s, CREAM, (int(g.x), int(g.y)), rr, 2)
            pygame.draw.circle(s, CREAM, (int(g.x - 4), int(g.y - 5)), 4)
        for sp in self.sparks:
            pygame.draw.circle(s, sp.col, (int(sp.x), int(sp.y)), max(1, int(sp.r * sp.life / 0.4)))
        if self.flash > 0:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((80, 220, 255, int(60 * self.flash / 0.16)))
            s.blit(veil, (0, 0))
        s.blit(self.font_lg.render(TITLE, True, CYAN), self.font_lg.render(TITLE, True, CYAN).get_rect(center=(W // 2, 54)))
        s.blit(self.font_sm.render(HANDLE, True, VIOLET), self.font_sm.render(HANDLE, True, VIOLET).get_rect(center=(W // 2, 106)))
        s.blit(self.font_md.render(f"SCORE  {self.score}", True, GOLD), (70, 1630))
        s.blit(self.font_md.render(f"CHAIN  x{self.combo}", True, MAG), (W - 340, 1630))
        hint = self.font_sm.render("bend the sodalite beam through drifting gems", True, CREAM)
        s.blit(hint, hint.get_rect(center=(W // 2, 1690)))
        for tag, x, y, life, col in self.pops:
            img = self.font_md.render(tag, True, col)
            s.blit(img, img.get_rect(center=(int(x), int(y))))
        foot = self.font_sm.render("Q/E aim  A/D rotate  TAB select  R reset  ESC quit", True, (150, 170, 210))
        s.blit(foot, foot.get_rect(center=(W // 2, H - 28)))

    def handle(self, ev) -> None:
        if ev.type == pygame.QUIT:
            self.running = False
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self.running = False
            elif ev.key == pygame.K_r:
                self.reset()
            elif ev.key == pygame.K_TAB:
                self.sel = (self.sel + 1) % len(self.prisms)

    def play(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                self.handle(ev)
            keys = pygame.key.get_pressed()
            pr = self.prisms[self.sel]
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                pr.ang -= 2.4 * dt
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                pr.ang += 2.4 * dt
            if keys[pygame.K_q]:
                self.eang -= 1.4 * dt
            if keys[pygame.K_e]:
                self.eang += 1.4 * dt
            self.update(dt)
            self.draw(self.surf)
            self.screen.blit(self.surf, (0, 0))
            pygame.display.flip()

    def record_mp4(self, path: str) -> None:
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart", path,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        frames = FPS * 15
        for i in range(frames):
            self.update(1.0 / FPS)
            self.draw(self.surf)
            proc.stdin.write(pygame.image.tostring(self.surf, "RGB"))
            if i % 30 == 0:
                print(f"frame {i}/{frames}", flush=True)
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed: {rc}")
        print("wrote", path)


def main() -> None:
    record = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
    play = "--play" in sys.argv
    if record or not play:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.font.init()
    g = Game(record or not play)
    if record or not play:
        out = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/SODALITE_PRISM_ElbowOS.mp4")
        g.record_mp4(out)
    else:
        g.play()
    pygame.quit()


if __name__ == "__main__":
    main()
