import math
import sys
import os
import datetime
import random
import pygame

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Asteroid")


def quit_game():
    pygame.quit()
    sys.exit()


def load_image_convert_alpha(filename):
    return pygame.image.load(os.path.join('../resources/images', filename)).convert_alpha()


def load_sound(filename):
    return pygame.mixer.Sound(os.path.join('../resources/sounds', filename))


def draw_centered(surface1, surface2, position):
    rect = surface1.get_rect()
    rect = rect.move(position[0] - rect.width // 2, position[1] - rect.height // 2)
    surface2.blit(surface1, rect)


def rotate_center(image, rect, angle):
    rotate_image = pygame.transform.rotate(image, angle)
    rotate_rect = rotate_image.get_rect(center=rect.center)
    return rotate_image, rotate_rect


def distance(p, q):
    return math.sqrt((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2)


class GameObject(object):
    def __init__(self, position, image, speed=0):
        self.image = image
        self.position = list(position[:])
        self.speed = speed

    def draw_on(self):
        draw_centered(self.image, screen, self.position)

    def size(self):
        return max(self.image.get_height(), self.image.get_width())

    def radius(self):
        return self.image.get_width() / 2


class Spaceship(GameObject):
    def __init__(self, position):
        super(Spaceship, self).__init__(position, load_image_convert_alpha('spaceship.png'))
        self.image = pygame.transform.scale(self.image, (50, 50))

        image_on = load_image_convert_alpha('spaceship_boost.png')
        self.image_on = pygame.transform.scale(image_on, (50, 50))
        self.direction = [0., -1.]
        self.is_throttle_on = False
        self.angle = 0

        self.active_missiles = []

    def draw_on(self):
        if self.is_throttle_on:
            new_image, rect = rotate_center(self.image_on, self.image_on.get_rect(), self.angle)
        else:
            new_image, rect = rotate_center(self.image, self.image.get_rect(), self.angle)

        draw_centered(new_image, screen, self.position)

    def move(self):
        self.direction[0] = math.sin(-math.radians(self.angle))
        self.direction[1] = -math.cos(math.radians(self.angle))

        self.position[0] += self.direction[0] * self.speed
        self.position[1] += self.direction[1] * self.speed

        if self.position[0] < 0:
            self.position[0] = SCREEN_WIDTH
        elif self.position[0] > SCREEN_WIDTH:
            self.position[0] = 0

        if self.position[1] < 0:
            self.position[1] = SCREEN_HEIGHT
        elif self.position[1] > SCREEN_HEIGHT:
            self.position[1] = 0

    def fire(self):
        adjust = [0, 0]
        adjust[0] = math.sin(-math.radians(self.angle)) * self.image.get_width()
        adjust[1] = -math.cos(math.radians(self.angle)) * self.image.get_height()
        new_missile = Missile((self.position[0] + adjust[0], self.position[1] + adjust[1] / 2), self.angle)
        self.active_missiles.append(new_missile)


class Missile(GameObject):
    def __init__(self, position, angle, speed=15):
        super(Missile, self).__init__(position, load_image_convert_alpha('missile.png'))
        self.image = pygame.transform.scale(self.image, (10, 10))
        self.angle = angle
        self.distance = 0.
        self.direction = [0., 0.]
        self.speed = speed

    def move(self):
        self.direction[0] = math.sin(-math.radians(self.angle))
        self.direction[1] = -math.cos(math.radians(self.angle))
        self.position[0] += self.direction[0] * self.speed
        self.position[1] += self.direction[1] * self.speed
        self.distance += self.speed

        if self.position[0] < 0:
            self.position[0] = SCREEN_WIDTH
        elif self.position[0] > SCREEN_WIDTH:
            self.position[0] = 0

        if self.position[1] < 0:
            self.position[1] = SCREEN_HEIGHT
        elif self.position[1] > SCREEN_HEIGHT:
            self.position[1] = 0


class Rock(GameObject):
    def __init__(self, position, size, speed=4):
        if size in {"large", "medium", "small"}:
            str_filename = "rock_" + str(size) + ".png"
            super(Rock, self).__init__(position, load_image_convert_alpha(str_filename))
            self.size = size

        self.position = list(position)

        self.speed = speed

        if bool(random.getrandbits(1)):
            rand_x = random.random() * -1
        else:
            rand_x = random.random()

        if bool(random.getrandbits(1)):
            rand_y = random.random() * -1
        else:
            rand_y = random.random()

        self.direction = [rand_x, rand_y]

    def move(self):
        self.position[0] += self.direction[0] * self.speed
        self.position[1] += self.direction[1] * self.speed


class Game(object):
    PLAYING, DYING, GAME_OVER, STARTING = range(4)
    REFRESH, START, RESTART = range(pygame.USEREVENT, pygame.USEREVENT + 3)

    def __init__(self):
        self.welcome_asteroids = None
        self.welcome_desc = None
        self.min_rock_distance = None
        self.lives = None
        self.score = None
        self.spaceship = None
        self.missiles = None
        self.rocks = None
        self.state = None
        self.counter = 0

        self.bg_color = 0, 0, 0

        self.die_sound = load_sound('die.wav')
        self.die_sound.set_volume(0.05)
        self.missile_sound = load_sound('fire.wav')
        self.missile_sound.set_volume(0.03)

        self.big_font = pygame.font.Font(None, 100)
        self.medium_font = pygame.font.Font(None, 50)
        self.small_font = pygame.font.Font(None, 25)
        self.game_over_text = self.big_font.render('GAME OVER',
                                                   True, (255, 0, 0))

        lives_image = load_image_convert_alpha('spaceship.png')
        self.lives_image = pygame.transform.scale(lives_image, (30, 30))

        self.FPS = 30
        pygame.time.set_timer(self.REFRESH, 1000 // self.FPS)

        self.death_distances = {"large": 90, "medium": 65, "small": 40}
        self.do_welcome()
        self.fire_time = datetime.datetime.now()

    def do_welcome(self):
        self.state = Game.STARTING
        self.welcome_asteroids = self.big_font.render("Asteroid", True, (255, 215, 0))
        self.welcome_desc = self.medium_font.render(
            "Click anywhere/press Enter", True, (35, 107, 142))

    def do_init(self):
        self.rocks = []
        self.min_rock_distance = 350

        self.start()

        for i in range(4):
            self.make_rock()

        self.lives = 3
        self.score = 0
        self.counter = 0

    def make_rock(self, size="large", pos=None):
        margin = 200

        if pos is None:
            rand_x = random.randint(margin, SCREEN_WIDTH - margin)
            rand_y = random.randint(margin, SCREEN_HEIGHT - margin)

            while distance((rand_x, rand_y), self.spaceship.position) < self.min_rock_distance:
                rand_x = random.randint(0, SCREEN_WIDTH)
                rand_y = random.randint(0, SCREEN_HEIGHT)

            temp_rock = Rock((rand_x, rand_y), size)

        else:
            temp_rock = Rock(pos, size)

        self.rocks.append(temp_rock)

    def start(self):
        self.spaceship = Spaceship((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.missiles = []

        self.state = Game.PLAYING

    def run(self):
        while True:
            event = pygame.event.wait()

            if event.type == pygame.QUIT:
                quit_game()

            elif event.type == Game.REFRESH:

                if self.state != Game.STARTING:

                    keys = pygame.key.get_pressed()

                    if keys[pygame.K_SPACE]:
                        new_time = datetime.datetime.now()
                        if new_time - self.fire_time > \
                                datetime.timedelta(seconds=0.15):
                            self.spaceship.fire()
                            self.missile_sound.play()
                            self.fire_time = new_time

                    if self.state == Game.PLAYING:

                        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                            self.spaceship.angle -= 10
                            self.spaceship.angle %= 360
                            if self.spaceship.speed > 0:
                                self.spaceship.speed -= 0.1

                        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                            self.spaceship.angle += 10
                            self.spaceship.angle %= 360
                            if self.spaceship.speed > 0:
                                self.spaceship.speed -= 0.1

                        if keys[pygame.K_UP] or keys[pygame.K_w]:
                            self.spaceship.is_throttle_on = True

                            if self.spaceship.speed < 20:
                                self.spaceship.speed += 1
                        else:
                            self.spaceship.is_throttle_on = False

                        if len(self.spaceship.active_missiles) > 0:
                            self.missiles_physics()

                        if len(self.rocks) > 0:
                            self.rocks_physics()

                        self.physics()

                self.draw()

            elif event.type == Game.START:
                pygame.time.set_timer(Game.START, 0)
                if self.lives < 1:
                    self.game_over()
                else:
                    self.rocks = []
                    for i in range(4):
                        self.make_rock()
                    self.start()

            elif event.type == Game.RESTART:
                pygame.time.set_timer(Game.RESTART, 0)
                self.state = Game.STARTING

            elif event.type == pygame.MOUSEBUTTONDOWN and self.state == Game.STARTING:
                self.do_init()

            elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and self.state == Game.STARTING:
                self.do_init()

    def game_over(self):
        self.state = Game.GAME_OVER
        pygame.time.set_timer(Game.RESTART, 3000)

    def die(self):
        self.lives -= 1
        self.counter = 0
        self.state = Game.DYING
        self.die_sound.play()
        delay = int((self.die_sound.get_length() + 1) * 1000)
        pygame.time.set_timer(Game.START, delay)

    def physics(self):
        if self.state == Game.PLAYING:
            self.spaceship.move()

    def missiles_physics(self):

        if len(self.spaceship.active_missiles) > 0:
            for missile in self.spaceship.active_missiles:
                missile.move()

                for rock in self.rocks:
                    if rock.size == "large":
                        if distance(missile.position, rock.position) < 80:
                            self.rocks.remove(rock)
                            if missile in self.spaceship.active_missiles:
                                self.spaceship.active_missiles.remove(missile)
                            self.make_rock("medium", (rock.position[0] + 10, rock.position[1]))
                            self.make_rock("medium", (rock.position[0] - 10, rock.position[1]))
                            self.score += 20

                    elif rock.size == "medium":
                        if distance(missile.position, rock.position) < 55:
                            self.rocks.remove(rock)
                            if missile in self.spaceship.active_missiles:
                                self.spaceship.active_missiles.remove(missile)
                            self.make_rock("small",
                                           (rock.position[0] + 10, rock.position[1]))
                            self.make_rock("small",
                                           (rock.position[0] - 10, rock.position[1]))
                            self.score += 50
                    else:
                        if distance(missile.position, rock.position) < 30:
                            self.rocks.remove(rock)
                            if missile in self.spaceship.active_missiles:
                                self.spaceship.active_missiles.remove(missile)

                            if len(self.rocks) < 10:
                                self.make_rock()

                            self.score += 100

                if missile in self.spaceship.active_missiles and missile.distance > SCREEN_WIDTH - 100:
                    self.spaceship.active_missiles.remove(missile)

    def rocks_physics(self):
        if len(self.rocks) > 0:

            for rock in self.rocks:
                rock.move()

                if distance(rock.position, self.spaceship.position) < \
                        self.death_distances[rock.size]:
                    self.die()

                elif distance(rock.position, (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)) > \
                        math.sqrt((SCREEN_WIDTH / 2) ** 2 + (SCREEN_HEIGHT / 2) ** 2):

                    self.rocks.remove(rock)
                    if len(self.rocks) < 10:
                        self.make_rock(rock.size)

    def draw(self):
        screen.fill(self.bg_color)

        if self.state != Game.STARTING:
            self.spaceship.draw_on()

            if len(self.spaceship.active_missiles) > 0:
                for missile in self.spaceship.active_missiles:
                    missile.draw_on()

            if len(self.rocks) > 0:
                for rock in self.rocks:
                    rock.draw_on()

            if self.state == Game.PLAYING:

                self.counter += 1

                if self.counter == 20 * self.FPS:

                    if len(self.rocks) < 15:
                        self.make_rock()

                    if self.min_rock_distance < 200:
                        self.min_rock_distance -= 50

                    self.counter = 0

            scores_text = self.medium_font.render(str(self.score),
                                                  True, (0, 155, 0))
            draw_centered(scores_text, screen,
                          (SCREEN_WIDTH - scores_text.get_width(), scores_text.get_height() -
                           10))

            if self.state == Game.GAME_OVER or self.state == Game.STARTING:
                draw_centered(self.game_over_text, screen,
                              (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))

            for i in range(self.lives):
                draw_centered(self.lives_image, screen,
                              (self.lives_image.get_width() * i * 1.2 + 40,
                               self.lives_image.get_height() // 2 + 10))

        else:
            draw_centered(self.welcome_asteroids, screen,
                          (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
                           - self.welcome_asteroids.get_height()))

            draw_centered(self.welcome_desc, screen,
                          (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
                           + self.welcome_desc.get_height()))

        pygame.display.flip()


Game().run()
quit_game()
