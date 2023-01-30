from __future__ import division, print_function, unicode_literals

# This code is so you can run the samples without installing the package
# import sys
# import os
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

import random
import math
import time
from colour import Color
from pyglet import clock

import cocos
from cocos.layer import *
from cocos import text

import cocos.collision_model as cm
import cocos.euclid as eu
import cocos.actions as ac


class BackgroundLayer(Layer):
    def __init__(self):
        super(BackgroundLayer, self).__init__()
        self.img = pyglet.resource.image('res/background.png')


    def draw(self):
        glPushMatrix()
        self.transform()
        self.img.blit(0, 0)
        glPopMatrix()

class HealthSprite(cocos.sprite.Sprite):
    def __init__(self, healthy, cshape):
        if healthy:
            super(HealthSprite, self).__init__(pyglet.resource.image('res/sprites/full_health.png'))
        else:
            super(HealthSprite, self).__init__(pyglet.resource.image('res/sprites/empty_health.png'))
        self.scale = (50 * 1.05) * ShipsAndLasers.scale_x / (self.image.width / 2.0)
        self.cshape = cshape
        self.update_center(self.cshape.center)


    def update_center(self, cshape_center):
        """cshape_center must be eu.Vector2"""
        self.position = ShipsAndLasers.world_to_view(self,cshape_center)
        self.cshape.center = cshape_center

class HealthText(cocos.sprite.Sprite):
    def __init__(self, cshape):
        super(HealthText, self).__init__(pyglet.resource.image('res/sprites/health_underline.png'))
        self.scale = (175 * 1.05) * ShipsAndLasers.scale_x / (self.image.width / 2.0)
        self.cshape = cshape

        tx, ty = self.cshape.r, self.cshape.r

        self.title = text.Label(
            "Health", (tx - 300, ty + 75), font_name='Gill Sans',
            font_size=72, anchor_x='center', anchor_y='bottom', color=(255,215,0, 255))
        self.add(self.title)
        self.update_center(self.cshape.center)


    def update_center(self, cshape_center):
        """cshape_center must be eu.Vector2"""
        self.position = ShipsAndLasers.world_to_view(self,cshape_center)
        self.cshape.center = cshape_center

class CreditSprite(cocos.sprite.Sprite):
    def __init__(self, credits):
        super(CreditSprite, self).__init__(pyglet.resource.image('res/sprites/credit_underline.png'))
        x, y = director.get_window_size()
        self.scale = (175 * 1.05) * ShipsAndLasers.scale_x / (self.image.width / 2.0)

        self.cshape = cm.CircleShape(eu.Vector2(x - (x//10),0 + (y//16)), ShipsAndLasers.scale_x*5)

        tx, ty = self.cshape.r, self.cshape.r

        self.title = text.Label(
            "Credits", (tx - 100, ty + 25), font_name='Gill Sans',
            font_size=64, anchor_x='center', anchor_y='bottom', color=(255,215,0, 255))
        self.add(self.title)
        line_text = text.Label(
            credits, (tx + 200, ty + 25), font_name='Gill Sans',
            font_size=64, anchor_x='center', anchor_y='bottom')
        self.add(line_text)
        self.update_center(self.cshape.center)

    def update_center(self, cshape_center):
        """cshape_center must be eu.Vector2"""
        self.position = ShipsAndLasers.world_to_view(self,cshape_center)
        self.cshape.center = cshape_center

class Actor(cocos.sprite.Sprite):
    palette = {}  # injected later

    def __init__(self, cx, cy, radius, btype, img, vel=None):
        super(Actor, self).__init__(img)
        # the 1.05 so that visual radius a bit greater than collision radius
        self.scale = (radius * 1.05) * ShipsAndLasers.scale_x / (self.image.width / 2.0)
        self.btype = btype
        self.cshape = cm.CircleShape(eu.Vector2(cx, cy), radius)
        self.update_center(self.cshape.center)
        if vel is None:
            vel = eu.Vector2(0.0, 0.0)
        self.vel = vel
        self.health = 100

    def update_center(self, cshape_center):
        """cshape_center must be eu.Vector2"""
        self.position = ShipsAndLasers.world_to_view(self,cshape_center)
        self.cshape.center = cshape_center


class Cooldown(Actor):
    def __init__(self, cx, cy, cooldownTime):
        super(Cooldown, self).__init__(cx,cy,ShipsAndLasers.consts["world"]["rPlayer"],"cooldown",pyglet.resource.image('res/sprites/cooldown.png'),None)
        self.cooldownTime = cooldownTime # how many ms the cooldown should be
        self.startTime = None
        self.cooldown = False
        self._opacity = 0  # 0->255 where 255 is solid
        self._update_color()
        self.origScale = self.scale
    def activate(self):
        self.cooldown = True
        self.startTime = (int(time.time()*1000))
    def animate(self):
        if self.cooldown:
            diff = int(time.time()*1000) - self.startTime
            if diff < self.cooldownTime:
                invProp = 1 - (diff / self.cooldownTime)
                self._opacity = 255
                self._update_color()
                self.scale = self.origScale * invProp
            else:
                self.cooldown = False
                self._opacity = 0
                self._update_color()
                self.scale = self.origScale



class Turret (Actor):
    def __init__(self, cx, cy, btype, img, cooldownTime, power):
        super(Turret, self).__init__(cx,cy,ShipsAndLasers.consts["world"]["rPlayer"],btype,img,None)
        self.cooldownTime = cooldownTime # how many ms the cooldown should be
        self.power = power # 1 -> 100, where 100 destroys the target instantly
        self.threshold = 100 # will take 100 clicks at 100 power to destroy a target
        self.destroyedTime = None # counts the clicks for the cooldown
        self.firing = False
        self.cooldown = False
        self.lastTarget = None
        self.cooldownIcon = Cooldown(cx, cy, cooldownTime)
    def turnTowards(self, target, dt):
        if self.destroyedTime == None or (int(time.time()*1000) - self.destroyedTime) > self.cooldownTime:
            if self.destroyedTime != None:
                self.destroyedTime = None
                self.cooldown = False
            if target.health <= 0 and self.firing and self.lastTarget == target:
                self.firing = False
                self.cooldown = True
                self.lastTarget = None
                self.destroyedTime = int(time.time() * 1000)
                self.cooldownIcon.activate()
                return "destroyed"
            elif self.firing and self.lastTarget == target:
                self.__shoot(target, dt)
                return "firing"
            elif self.firing and self.lastTarget != target:
                self.__shoot(target, dt)
                self.lastTarget = target
                return "firing"
            elif self.firing == False and self.cooldown == False:
                self.firing = True
                self.lastTarget = target
                self.__shoot(target, dt)
                return "firing"
        else:
            return "cooldown"


    def __shoot(self, target, dt):
        dx = self.cshape.center.x - target.cshape.center.x
        dy = self.cshape.center.y - target.cshape.center.y
        angle = (math.atan(dx / dy) * 180 / math.pi) + 180  # need 180* offset
        self.update(rotation=angle)
        target.health -= (self.power / 100.0) * (dt*100) # dt is in seconds



class MessageLayer(cocos.layer.Layer):

    """Transitory messages over worldview

    Responsability:
    full display cycle for transitory messages, with effects and
    optional callback after hiding the message.
    """

    def show_message(self, msg, callback=None):
        w, h = director.get_window_size()

        self.msg = cocos.text.Label(msg,
                                    font_size=52,
                                    font_name=ShipsAndLasers.consts['view']['font_name'],
                                    anchor_y='center',
                                    anchor_x='center',
                                    width=w,
                                    multiline=True,
                                    align="center")
        self.msg.position = (w / 2.0, h)

        self.add(self.msg)

        actions = (
            ac.Show() + ac.Accelerate(ac.MoveBy((0, -h / 2.0), duration=0.5)) +
            ac.Delay(1) +
            ac.Accelerate(ac.MoveBy((0, -h / 2.0), duration=0.5)) +
            ac.Hide()
        )

        if callback:
            actions += ac.CallFunc(callback)

        self.msg.do(actions)

class Worldview(cocos.layer.Layer):

    """
    Responsabilities:
        Generation: random generates a level
        Initial State: Set initial playststate
        Play: updates level state, by time and user input. Detection of
        end-of-level conditions.
        Level progression.
    """
    is_event_handler = True

    def __init__(self, thisShipsAndLasers, fn_show_message=None):
        super(Worldview, self).__init__()
        self.fn_show_message = fn_show_message
        self.thisShipsAndLasers = thisShipsAndLasers

        # basic geometry
        world = self.thisShipsAndLasers.consts['world']
        self.width = world['width']  # world virtual width
        self.height = world['height']  # world virtual height
        self.rPlayer = world['rPlayer']  # player radius in virtual space
        self.wall_scale_min = world['wall_scale_min']
        self.wall_scale_max = world['wall_scale_max']
        self.angular_velocity = world['angular_velocity']
        self.accel = world['accel']

        # load resources:
        self.pics = {}
        self.pics["red_ship"] = pyglet.resource.image('res/sprites/red_ship.png').get_transform(rotate=90) # (237, 54, 36)
        self.pics["pink_ship"] = pyglet.resource.image('res/sprites/pink_ship.png').get_transform(rotate=90) # (255,0,212)
        self.pics["green_ship"] = pyglet.resource.image('res/sprites/green_ship.png').get_transform(rotate=90) # (169,255,23)
        self.pics["blue_ship"] = pyglet.resource.image('res/sprites/blue_ship.png').get_transform(rotate=90) # (0,111,255)

        self.pics["red_turret"] = pyglet.resource.image('res/sprites/red_turret.png').get_transform(rotate=90)
        self.pics["pink_turret"] = pyglet.resource.image('res/sprites/pink_turret.png').get_transform(rotate=90)
        self.pics["green_turret"] = pyglet.resource.image('res/sprites/green_turret.png').get_transform(rotate=90)
        self.pics["blue_turret"] = pyglet.resource.image('res/sprites/blue_turret.png').get_transform(rotate=90)
        self.pics["rgb_turret"] = pyglet.resource.image('res/sprites/rgb_turret.png').get_transform(rotate=90)



        self.spawn_clicks = 2000 # spawn a new ship every spawn_clicks ms


        cell_size = self.rPlayer * self.wall_scale_max * 2.0 * 1.25

        self.collman = cm.CollisionManagerGrid(0.0, self.width,
                                               0.0, self.height,
                                               cell_size, cell_size)

        self.ships = []
        self.activeShips = []
        self.activeTurrets = [None for x in range(0, self.thisShipsAndLasers.consts["game"]["num_turrets"])]
        self.lasers = []
        self.z = 0

        self.accumulatedTime = 0

        self.colorList = list(Color("red").range_to(Color("green"), 100)) + list(Color("green").range_to(Color("blue"), 100)) + list(Color("blue").range_to(Color("red"), 100))
        self.cycleTime = 2000 # in ms, how long it should take to cycle through RGB
        self.cycleStart = int(time.time() * 1000)

        self.turretList = self.thisShipsAndLasers.getTurrets()

        self.currentLevel = self.thisShipsAndLasers.getLevel()

        self.health = self.thisShipsAndLasers.health

        self.toRemove = set()

        @director.window.event
        def on_close():
            self.empty_level()
            self.thisShipsAndLasers.levelMoney = 0


        self.unschedule(self.update)
        self.schedule(self.update)

        if self.currentLevel == 0:
            self.ladder_begin()
        else:
            self.level_next()



    def makeTurret(self, t_type, index): # t_type == "red", "blue", "pink", "green", "rgb"
        if self.activeTurrets[index] is None:
            if t_type == "red":
                t = Turret(self.thisShipsAndLasers.turretLocations[index][0], self.thisShipsAndLasers.turretLocations[index][1],
                                          t_type, self.pics["red_turret"], self.thisShipsAndLasers.consts["game"]["norm_turret_cooldown_ms"],
                                          self.thisShipsAndLasers.consts["game"]["norm_turret_power"])
            elif t_type == "blue":
                t = Turret(self.thisShipsAndLasers.turretLocations[index][0], self.thisShipsAndLasers.turretLocations[index][1],
                                          t_type, self.pics["blue_turret"], self.thisShipsAndLasers.consts["game"]["norm_turret_cooldown_ms"],
                                          self.thisShipsAndLasers.consts["game"]["norm_turret_power"])
            elif t_type == "green":
                t = Turret(self.thisShipsAndLasers.turretLocations[index][0], self.thisShipsAndLasers.turretLocations[index][1],
                                          t_type, self.pics["green_turret"], self.thisShipsAndLasers.consts["game"]["norm_turret_cooldown_ms"],
                                          self.thisShipsAndLasers.consts["game"]["norm_turret_power"])
            elif t_type == "pink":
                t = Turret(self.thisShipsAndLasers.turretLocations[index][0], self.thisShipsAndLasers.turretLocations[index][1],
                                          t_type, self.pics["pink_turret"], self.thisShipsAndLasers.consts["game"]["norm_turret_cooldown_ms"],
                                          self.thisShipsAndLasers.consts["game"]["norm_turret_power"])
            elif t_type == "rgb":
                t = Turret(self.thisShipsAndLasers.turretLocations[index][0], self.thisShipsAndLasers.turretLocations[index][1],
                                          t_type, self.pics["rgb_turret"], self.thisShipsAndLasers.consts["game"]["rgb_turret_cooldown_ms"],
                                          self.thisShipsAndLasers.consts["game"]["rgb_turret_power"])
            else:
                return False
            t.update(rotation=180)
            self.activeTurrets[index] = t
            self.add(t, z=self.z)
            self.add(t.cooldownIcon, z=self.z+1)
            self.z += 2

    def cycleRGB(self, turret):
        dif = int(time.time()*1000) - self.cycleStart
        if dif >= self.cycleTime:
            dif = 0
            self.cycleStart = int(time.time()*1000)
        turret.color = (x * 255 for x in self.colorList[int((1.0*dif/self.cycleTime) * len(self.colorList))].get_rgb())
        return turret.color

    def ladder_begin(self):
        self.empty_level()
        msg = 'ships and lasers'
        self.generate_random_level()
        self.fn_show_message(msg, callback=self.level_start)

    def level_start(self):
        self.win_status = 'undecided'

    def level_conquered(self):
        self.win_status = 'intermission'
        msg = 'level %d\nconquered !' % self.thisShipsAndLasers.getLevel()
        self.thisShipsAndLasers.currentMoney += self.thisShipsAndLasers.levelMoney
        self.thisShipsAndLasers.levelMoney = 0
        self.thisShipsAndLasers.incrementLevel()
        self.fn_show_message(msg, callback=director.window.close)

    def level_losed(self):
        self.win_status = 'losed'
        self.thisShipsAndLasers.currentMoney = self.thisShipsAndLasers.consts["game"]["start_money"]
        self.thisShipsAndLasers.purchasedTurrets = [None for x in range(0, len(self.thisShipsAndLasers.purchasedTurrets))]
        self.thisShipsAndLasers.currentLevel = 0
        self.thisShipsAndLasers.health = 2
        msg = 'sorry, you lost!'
        self.fn_show_message(msg, director.window.close)

    def level_next(self):
        self.empty_level()
        self.generate_random_level()
        msg = 'level ' + str(self.thisShipsAndLasers.getLevel())
        self.fn_show_message(msg, callback=self.level_start)

    def empty_level(self):
        # del old actors, if any
        for node in self.get_children():
            self.remove(node)
        assert len(self.children) == 0
        self.activeTurrets = [None for x in range(0, self.thisShipsAndLasers.consts["game"]["num_turrets"])]
        self.ships = []
        self.activeShips = []

        self.toRemove.clear()

        self.win_status = 'intermission'  # | 'undecided' | 'conquered' | 'losed'


    def generate_random_level(self):

        for i, t in enumerate(self.turretList):
            self.makeTurret(t, i)

        self.creditSprite = CreditSprite(str(self.thisShipsAndLasers.getMoney() + self.thisShipsAndLasers.levelMoney))
        self.add(self.creditSprite)
        self.healthMonitor()

        #generate ships

        imgs = [self.pics['red_ship'], self.pics['blue_ship'], self.pics['green_ship'], self.pics['pink_ship']]
        velFactor = 1

        lvl = self.thisShipsAndLasers.getLevel()

        self.spawnFreq = 1

        if lvl <=5:
            self.spawnFreq = .8
        elif lvl > 5 and lvl <=12:
            self.spawnFreq = .7
        elif lvl > 12 and lvl <= 22:
            self.spawnFreq = .6
        elif lvl > 22:
            self.spawnFreq = .5

        if lvl <= 4:
            probs = [1,0,0,0]
        elif lvl > 4 and lvl <= 9:
            probs = [.5,.5,0,0]
            velFactor = 1.2
        elif lvl > 9 and lvl <=14:
            probs = [1/3, 1/3, 1/3, 0]
            velFactor = 1.5
        elif lvl > 14 <=18:
            velFactor = 2
            probs = [.25,.25,.25,.25]
        elif lvl > 18:
            velFactor = 2.2
            # probs = [1/6, 1/3, 1/3, 1/6]

        num_ships = (self.thisShipsAndLasers.getLevel() + 1) * self.thisShipsAndLasers.consts["game"]["wave_difficulty"]

        thisImgs = random.choices(imgs, weights=probs, k=num_ships)



        for i in thisImgs:
            sx, sy = random.randint(0, int(.05 * self.width)), random.randint(int(.15 * self.height),
                                                                              int(.7 * self.height))
            s_vel = eu.Vector2(random.randint(math.floor(.5 * self.thisShipsAndLasers.consts["game"]["ship_avg_vel"] * velFactor),
                                              math.floor(1.5 * self.thisShipsAndLasers.consts["game"]["ship_avg_vel"]) * velFactor), 0)
            if i == self.pics['red_ship']:
                s_type = "red"
            elif i == self.pics['blue_ship']:
                s_type = "blue"
            elif i == self.pics['green_ship']:
                s_type = "green"
            elif i == self.pics['pink_ship']:
                s_type = "pink"
            else:
                return "error, invalid ship type"
            s_actor = Actor(sx, sy, self.rPlayer, s_type, i, s_vel)
            self.ships.append(s_actor)


    def healthMonitor(self):
        x, y = director.get_window_size()

        h1s = cm.CircleShape(eu.Vector2(x - (x // 16), 0 + (15 * y // 16)), ShipsAndLasers.scale_x * 5)
        h2s = cm.CircleShape(eu.Vector2(x - (2 * x // 16), 0 + (15 * y // 16)), ShipsAndLasers.scale_x * 5)
        ht = cm.CircleShape(eu.Vector2(x - (3 * x // 24) - 15, (15 * y // 16) - 25), ShipsAndLasers.scale_x * 5)
        if self.thisShipsAndLasers.health == 2:
            self.h1sprite = HealthSprite(True, h1s)
            self.h2sprite = HealthSprite(True, h2s)
            self.add(self.h1sprite)
            self.add(self.h2sprite)
        elif self.thisShipsAndLasers.health == 1:
            self.h1sprite = HealthSprite(False, h1s)
            self.h2sprite = HealthSprite(True, h2s)
            self.add(self.h1sprite)
            self.add(self.h2sprite)
        else:
            self.h1sprite = HealthSprite(False, h1s)
            self.h2sprite = HealthSprite(False, h2s)
            self.add(self.h1sprite)
            self.add(self.h2sprite)
        self.htext = HealthText(ht)
        self.add(self.htext)

    def update(self, in_dt):

        # if not playing dont update model
        if self.win_status != 'undecided':
            return

        self.accumulatedTime += (in_dt * 1000)

        if self.accumulatedTime >= self.thisShipsAndLasers.consts["game"]["ship_spawn_rate_ms"] * self.spawnFreq: # spawn another ship!
        # if len(self.activeShips) == 0: # spawn another ship!
            if len(self.ships) > 0:
                thisShip = self.ships.pop()
                thisShip.update(rotation=90)
                thisShip.update_center(thisShip.cshape.center)
                self.add(thisShip, z=self.z)
                self.activeShips.append(thisShip)
                self.collman.add(thisShip)
                self.accumulatedTime = 0
                self.z += 1
            else:
                if len(self.activeShips) == 0:
                    self.level_conquered()

        # update collman & object positions
        self.collman.clear()
        for node in self.activeShips:
            self.collman.add(node)

            ppos = node.cshape.center
            newPos = ppos
            r = node.cshape.r
            newVel = node.vel
            dt = in_dt
            while dt > 1.e-6:
                newPos = ppos + dt * newVel
                consumed_dt = dt
                # what about screen boundaries ? if colision bounce
                # if newPos.x < r:
                #     consumed_dt = (r - ppos.x) / newVel.x
                #     newPos = ppos + consumed_dt * newVel
                #     newVel = -ShipsAndLasers.reflection_y(self,newVel)
                if newPos.x > (self.width - r):
                    dt = 0
                    self.toRemove.add(node)
                    self.activeShips.remove(node)
                    self.thisShipsAndLasers.health -= 1
                # if newPos.y < r:
                #     consumed_dt = (r - ppos.y) / newVel.y
                #     newPos = ppos + consumed_dt * newVel
                #     newVel = reflection_y(newVel)
                # if newPos.y > (self.height - r):
                #     consumed_dt = (self.height - r - ppos.y) / newVel.y
                #     newPos = ppos + consumed_dt * newVel
                #     newVel = reflection_y(newVel)
                dt -= consumed_dt

            node.vel = newVel
            node.update_center(newPos)

        for l in self.lasers:
            self.remove(l)
        self.lasers.clear()

        for t in self.activeTurrets:
            if t is not None:
                # ppos = t.cshape.center
                if t.btype == "rgb": # update rgb on turrets!
                    curRGB = self.cycleRGB(t)
                    curRGB.append(255)
                # dist = ShipsAndLasers.consts["world"]["width"] * ShipsAndLasers.consts["world"]["height"]
                dist = 0
                closest = None
                for node in self.activeShips:
                    # if node.cshape.distance(t.cshape) < dist and (t.btype == node.btype or t.btype == "rgb"): # closet ship to turret and is same color
                    #     dist = node.cshape.distance(t.cshape)
                    #     closest = node
                    if node.cshape.center.x > dist and (t.btype == node.btype or t.btype == "rgb"): # ship furthest to the right of the screen and the same color
                        dist = node.cshape.center.x
                        closest = node



                if closest is not None:
                    status = t.turnTowards(closest, in_dt)
                    if status == "ready":
                        status = t.turnTowards(closest, in_dt)
                    if status == "firing": # we're shooting at the target
                        if t.btype == "red":
                            line = cocos.draw.Line(t.cshape.center, closest.cshape.center, (237, 54, 36, 255),
                                   stroke_width=int(self.thisShipsAndLasers.consts["game"]["norm_turret_power"]/(ShipsAndLasers.sim_speed * 10)))
                        elif t.btype == "blue":
                            line = cocos.draw.Line(t.cshape.center, closest.cshape.center, (0, 111, 255, 255),
                                   stroke_width=int(self.thisShipsAndLasers.consts["game"]["norm_turret_power"] / (ShipsAndLasers.sim_speed * 10)))

                        elif t.btype == "green":
                            line = cocos.draw.Line(t.cshape.center, closest.cshape.center, (169, 255, 23, 255),
                                   stroke_width=int(self.thisShipsAndLasers.consts["game"]["norm_turret_power"] / (ShipsAndLasers.sim_speed * 10)))
                        elif t.btype == "pink":
                            line = cocos.draw.Line(t.cshape.center, closest.cshape.center, (255, 0, 212, 255),
                                   stroke_width=int(self.thisShipsAndLasers.consts["game"]["norm_turret_power"] / (ShipsAndLasers.sim_speed * 10)))
                        elif t.btype == "rgb": # rgb!
                            line = cocos.draw.Line(t.cshape.center, closest.cshape.center, tuple(x for x in curRGB),
                                   stroke_width=int(self.thisShipsAndLasers.consts["game"]["rgb_turret_power"] / (ShipsAndLasers.sim_speed * 10)))

                        self.lasers.append(line)
                        self.add(line)
                    elif status == "destroyed":
                        self.toRemove.add(closest)
                        self.activeShips.remove(closest)
                        self.thisShipsAndLasers.levelMoney += self.thisShipsAndLasers.consts["game"]["ship_value"]
                    elif status == "cooldown": #can't do anything during cooldown
                        pass
                t.cooldownIcon.animate()

        # update money!
        self.remove(self.creditSprite)
        self.creditSprite = CreditSprite(str(self.thisShipsAndLasers.getMoney() + self.thisShipsAndLasers.levelMoney))
        self.add(self.creditSprite)


        # update health status
        self.remove(self.h1sprite)
        self.remove(self.h2sprite)
        self.remove(self.htext)
        self.healthMonitor()


        # at end of frame do removes; as collman is fully regenerated each frame
        # theres no need to update it here.

        if self.thisShipsAndLasers.health <= 0:
            self.level_losed()

        for node in self.toRemove:
            self.remove(node)
        self.toRemove.clear()

    # def open_gate(self):
    #     self.gate.color = Actor.palette['gate']

    # def on_key_press(self, k, m):
    #     binds = self.bindings
    #     if k in binds:
    #         self.buttons[binds[k]] = 1
    #         return True
    #     return False
    #
    # def on_key_release(self, k, m):
    #     binds = self.bindings
    #     if k in binds:
    #         self.buttons[binds[k]] = 0
    #         return True
    #     return False



class ShipsAndLasers:


    fe = 1.0e-4

    sim_speed = 1
    consts = {}
    scale_y, scale_x = 0,0
    @staticmethod
    def _refreshParams():
        ShipsAndLasers.consts = {
            "window": {
                "width": 800,
                "height": 600,
                "vsync": True,
                "resizable": True
            },
            "world": {
                # "sim_speed": 1,
                "width": 800,
                "height": 600,
                "rPlayer": 14,
                "wall_scale_min": 0.75,  # relative to player
                "wall_scale_max": 2.25,  # relative to player
                # "topSpeed": 100.0 * sim_speed,
                "angular_velocity": 240.0 * ShipsAndLasers.sim_speed,  # degrees / s
                "accel": 85.0 * ShipsAndLasers.sim_speed,
                # "bindings": {
                #     key.LEFT: 'left',
                #     key.RIGHT: 'right',
                #     key.UP: 'up',
                # }
            },
            "view": {
                # as the font file is not provided it will decay to the default font;
                # the setting is retained anyway to not downgrade the code
                "font_name": 'Axaxax',
            },
            "game": {
                "wave_difficulty": 4, # this * wavenum = total ships
                "ship_spawn_rate_ms": 1000 * (1/ShipsAndLasers.sim_speed),
                "ship_avg_vel": 100 * ShipsAndLasers.sim_speed,
                "ship_value": 25, # how much money per destroyed ship
                "start_money": 1600,
                "num_turrets": 5,
                "norm_turret_power": 120 * ShipsAndLasers.sim_speed,
                "norm_turret_cooldown_ms": 1000 * (1/ShipsAndLasers.sim_speed),
                "norm_turret_cost": 600,
                "rgb_turret_power": 40 * ShipsAndLasers.sim_speed,
                "rgb_turret_cooldown_ms": 2000 * (1/ShipsAndLasers.sim_speed),
                "rgb_turret_cost": 1000,
            }
        }


        ShipsAndLasers.scale_y = ShipsAndLasers.consts["window"]["height"] / ShipsAndLasers.consts["world"]["height"]
        ShipsAndLasers.scale_x = ShipsAndLasers.consts["window"]["width"] / ShipsAndLasers.consts["world"]["width"]

    currentWorld = None

    def __init__(self):
        # world to view scales

        # evenly spaced turret locations, 85% of the way up the window
        # need this stupid function cause we can't call static variables from list comprehensions
        ShipsAndLasers._refreshParams()

        self.turretLocations = [
            [math.floor(self.consts["window"]["width"] / (self.consts["game"]["num_turrets"] + 1)) * (s + 1),
             self.consts["window"]["height"] * .85] for s in range(0, self.consts["game"]["num_turrets"])]

        self.purchasedTurrets = [None for s in range(0, self.consts["game"]["num_turrets"])]
        self.currentMoney = self.consts["game"]["start_money"]
        self.levelMoney = 0
        self.currentLevel = 0
        self.health = 2


    # provide an ordered list of turrets and their locations (location doesn't matter in gameplay)
    # ex: ["blue", None, "rgb", "red", "green"] in a game with 5 slots and has available money for purchase
    def setTurrets(self, turrets :list):
        thisCurrentMoney = self.currentMoney
        for t in self.purchasedTurrets: # count placed turret value to allow reordering/reconfiguring
            if t != None and t != "rgb":
                thisCurrentMoney += self.consts["game"]["norm_turret_cost"]
            elif t != None and t == "rgb":
                thisCurrentMoney += self.consts["game"]["rgb_turret_cost"]
        if len(turrets) != len(self.purchasedTurrets):
            return "Error, you must specify " + str(len(self.purchasedTurrets)) + " turret or None objects."
        print("you have " + str(thisCurrentMoney) + " credits to spend")
        for index, i in enumerate(turrets):
            if i is not None:
                if i == "red" or i == "blue" or i == "green" or i == "pink":
                    thisCurrentMoney -= self.consts["game"]["norm_turret_cost"]
                elif i == "rgb":
                    thisCurrentMoney -= self.consts["game"]["rgb_turret_cost"]
                else:
                    return "Error, invalid turret type. Valid types are \"red\", \"blue\", \"green\", \"pink\", and \"rgb\""
        if thisCurrentMoney < 0:
            return "Error, not enough credits to buy turret config. You have " + str(self.currentMoney) + " credits available."
        print("credits left over: " + str(thisCurrentMoney))
        self.currentMoney = thisCurrentMoney
        self.purchasedTurrets = turrets


    # update a game parameter
    def setSimSpeed(self, value):
        if value >=1 and value <=20:
            ShipsAndLasers.sim_speed = value
        else:
            return "Error, sim speed must be in range [1, 20]"
        ShipsAndLasers._refreshParams()

    def incrementLevel(self):
        self.currentLevel += 1

    def getLevel(self):
        return self.currentLevel

    def getMoney(self):
        return self.currentMoney

    def getTurrets(self):
        return self.purchasedTurrets

    def getTurretLocations(self):
        return self.turretLocations

    # class BackgroundSprite(cocos.sprite.Sprite):
    #     def __init__(self, img):
    #         super(ShipsAndLasers.BackgroundSprite, self ).__init__(img)
    #         self.scale = 1
    #         self.position = 0, 0
    #
            # self.img = pyglet.resource.image('res/background.png')
            # self.img.width, self.img.height = 1920, 1080
            # self.img.texture.width, self.img.texture.height = 1920, 1080
            # self.img.scale = scale_x, scale_y
        #
        # def draw( self ):
        #     glPushMatrix()
        #     self.transform()
        #     self.img.blit(0,0)
        #     glPopMatrix()


    def world_to_view(self, v):
        """world coords to view coords; v an eu.Vector2, returns (float, float)"""
        return v.x * self.scale_x, v.y * self.scale_y



    def reflection_y(self, a):
        assert isinstance(a, eu.Vector2)
        return eu.Vector2(a.x, -a.y)



    def nextWave(self):


        director.init(**self.consts['window'])
        # make window
        director.set_show_FPS(1)

        #pyglet.font.add_directory('.') # adjust as necessary if font included
        scene = cocos.scene.Scene()
        # palette = ShipsAndLasers.consts['view']['palette']
        # ShipsAndLasers.Actor.palette = palette
        # r, g, b = palette['bg']
        # scene.add(cocos.layer.ColorLayer(r, g, b, 255), z=-1)
        scene.add(BackgroundLayer())
        message_layer = MessageLayer()
        scene.add(message_layer, z=1)
        # scene.add(ShipsAndLasers.CreditsTextLayer("hello", ["hi1", "hi2"]))
        # if ShipsAndLasers.currentWorld == None:
        ShipsAndLasers.currentWorld = Worldview(self, fn_show_message=message_layer.show_message)
        # else:
        #     ShipsAndLasers.currentWorld = Worldview(self, fn_show_message=message_layer.show_message)
        # else:
        #     ShipsAndLasers.currentWorld.willResume = True
            # ShipsAndLasers.currentWorld
        # playview.add(BackgroundSprite(pyglet.resource.image('res/background.png')))
        scene.add(ShipsAndLasers.currentWorld, z=0)
        director.run(scene)


    # def reset(self):
    #     ShipsAndLasers.currentWorld = None
# game = ShipsAndLasers()
# game.setParam("sim_speed", 5)
# game.setTurrets(["red", "blue", None, None, "rgb"])
# game.nextWave()
# time.sleep(2000)
# game.nextWave()