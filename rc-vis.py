import pygame
from time import sleep
from RemoteController import JoystickController

def main():
    pygame.init()
    surface = pygame.display.set_mode((640, 480))
    pygame.display.set_caption('RC Visualizer')

    rc = JoystickController()
    rc.gain = 0.2
    rc.max_r = 20

    try:
        while True:
            (x,y,z), _, grip = rc.read()

            x = int(x)
            y = int(y)
            z = int(z)

            surface.fill((255,255,255))
            drawPosition(surface, (x,y))
            drawHeight(surface, z)
            drawGrip(surface, grip)
            pygame.display.flip()

            sleep(0.1)
    except KeyboardInterrupt:
        print('exiting')

    pygame.quit()


def drawPosition(surface, xy, center=(160,240), radius=120):
    # big circle
    pygame.draw.circle(surface, (200,200,200), center, radius)

    # cross
    len = 20
    pygame.draw.line(surface, (0,0,0), (center[0]+len, center[1]), (center[0]-len, center[1]), 2)
    pygame.draw.line(surface, (0,0,0), (center[0], center[1]+len), (center[0], center[1]-len), 2)

    # small circle
    xy = changeFrame(xy)
    pygame.draw.circle(surface, (0,0,0), xy, 7)

    # text
    font = pygame.font.SysFont(None, 24)
    img = font.render('Position:', True, (0,0,0))
    surface.blit(img, (center[0]-(img.get_width()/2), int((center[1]-radius) / 2)))

def drawHeight(surface, z, center=(400,240), height=240, width=40):
    # bar
    x1 = center[0] - width/2
    x2 = x1 + width
    y1 = center[1] - height/2
    pygame.draw.rect(surface, (200,200,200), (x1, y1, width, height))

    # height line
    z = y1 + height - z*12
    pygame.draw.line(surface, (0,0,0), (x1, z), (x2, z), 4)

    # text
    font = pygame.font.SysFont(None, 24)
    img = font.render('Height:', True, (0,0,0))
    surface.blit(img, (center[0]-(img.get_width()/2), (center[1]-height/2)/2))

def drawGrip(surface, grip, center=(530,200)):
    # title text
    font = pygame.font.SysFont(None, 24)
    img1 = font.render('Gripping:', True, (0,0,0))
    w,h = img1.get_width(), img1.get_height()
    x,y = center[0]-w/2, center[1]-10
    surface.blit(img1, (x,y))

    # status text
    font = pygame.font.SysFont(None, 36)
    if grip:
        img2 = font.render('TRUE', True, (0,0,255))
    else:
        img2 = font.render('FALSE', True, (200, 200, 200))
    w,h = img2.get_width(), img2.get_height()
    x,y = center[0]-w/2, center[1]+h
    surface.blit(img2, (x,y))

def changeFrame(xy, scaling=6, center=(200,240)):
    x = center[0] + xy[0]*scaling
    y = center[1] - xy[1]*scaling
    return (x,y)


if __name__=='__main__':
    main()
