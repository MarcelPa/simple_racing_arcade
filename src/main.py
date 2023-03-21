import os
import tempfile
from typing import Any, Dict, List, Tuple

import arcade
from PIL import Image, ImageDraw


SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_TITLE = "Simple Racer"

CAR_ASSET = "assets/ambulance.png"
CAR_WIDTH = 20
CAR_HEIGHT = 35

TRACKS = [
    {
        "track": "assets/racing_track.png",
        "start": (110, 360),
        "outer_bound": [
            (50, 250),
            (290, 50),
            (975, 50),
            (1100, 175),
            (1100, 225),
            (885, 285),
            (885, 360),
            (1230, 400),
            (1230, 575),
            (1115, 670),
            (280, 670),
            (50, 500),
        ],
        "inner_bound": [
            (200, 285),
            (355, 160),
            (880, 160),
            (640, 270),
            (640, 415),
            (800, 480),
            (1070, 490),
            (1040, 575),
            (350, 575),
            (200, 465),
        ],
    },
]

CAR_MASS = 1
DAMPING = 0.05
ACCELERATE_FORCE = 1250
BREAK_FORCE = 1250
MAX_VELOCITY = 100000
CAR_TURN_SPEED = 0.075
CAR_DRIFT = 0.35  # has to be [0.0,1.0); 0.0 means no drift


class Car(arcade.Sprite):
    """
    Car class.
    """

    def __init__(self):
        super().__init__(CAR_ASSET)


class Track(arcade.Sprite):
    """
    Track class.
    """

    def __init__(self, track: Dict[str, Any]):
        """
        Construct a Track based on an outer and an inner bound.
        """
        self.outer_box = track["outer_bound"]
        self.inner_box = track["inner_bound"]
        self.start = track["start"]

        # generate the track image
        image = Image.new("RGBA", (SCREEN_WIDTH, SCREEN_HEIGHT), color=(0, 0, 0, 0))
        image_draw = ImageDraw.Draw(image)
        image_draw.polygon(
            Track._flip_y(self.outer_box),
            fill=(128, 128, 128, 255),
            outline=(0, 0, 0, 255),
            width=3,
        )
        image_draw.polygon(
            Track._flip_y(self.inner_box),
            fill=(0, 0, 0, 0),
            outline=(0, 0, 0, 255),
            width=3,
        )
        self._alpha_track_mask = image.getchannel("A")

        # create a temporary file to create the sprite
        with tempfile.NamedTemporaryFile(suffix=".png") as png:
            save_file_name = png.name
        save_file_path = os.path.join(tempfile.gettempdir(), save_file_name)
        image.save(save_file_path, format="PNG")

        # run the constructor of Sprite
        super().__init__(save_file_path)

    def is_ontrack(self, x: int, y: int) -> bool:
        """
        Check if a point is on the track.
        """
        return arcade.is_point_in_polygon(
            x, y, self.outer_box
        ) and not arcade.is_point_in_polygon(x, y, self.inner_box)

    def _flip_y(points: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """
        The coordinates from pillow to arcade are flipped horizontally.
        """
        return [(x, SCREEN_HEIGHT - y) for x, y in points]


class Racer(arcade.Window):
    """
    Racer application class.
    """

    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(arcade.color.AMAZON)

        # sprites
        self.scene = None
        self.track = None
        self.car = None

        # physics
        self.physics_engine = None

        # controls
        self.accelerate: bool = False
        self.slowdown: bool = False
        self.turn_left: bool = False
        self.turn_right: bool = False

        # events
        self.out_of_track: bool = False

    def setup(self):
        self.scene = arcade.Scene()
        self.scene.add_sprite_list("Track")
        self.scene.add_sprite_list("Cars")

        self.track = Track(TRACKS[0])
        self.track.center_x, self.track.center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        self.scene.add_sprite("Track", self.track)

        self.car = Car()
        self.car.center_x, self.car.center_y = TRACKS[0]["start"]
        self.scene.add_sprite("Cars", self.car)

        self.physics_engine = arcade.PymunkPhysicsEngine(
            damping=DAMPING,
            gravity=(0, 0),
        )
        self.physics_engine.add_sprite(
            self.car,
            collision_type="player",
            mass=CAR_MASS,
            max_velocity=MAX_VELOCITY,
            body_type=arcade.PymunkPhysicsEngine.DYNAMIC,
        )

        # reset events
        self.out_of_track = False

    def on_key_press(self, key: int, modifiers: int):
        """Handle controls."""
        if key in [arcade.key.Q, arcade.key.ESCAPE]:
            exit(0)
        if key == arcade.key.R:
            self.setup()
        if key in [arcade.key.UP, arcade.key.W]:
            self.accelerate = True
        elif key in [arcade.key.DOWN, arcade.key.S]:
            self.slowdown = True
        if key in [arcade.key.LEFT, arcade.key.A]:
            self.turn_left = True
        elif key in [arcade.key.RIGHT, arcade.key.D]:
            self.turn_right = True

    def on_key_release(self, key: int, modifiers: int):
        """Handle controls."""
        if key in [arcade.key.UP, arcade.key.W]:
            self.accelerate = False
        if key in [arcade.key.DOWN, arcade.key.S]:
            self.slowdown = False
        if key in [arcade.key.LEFT, arcade.key.A]:
            self.turn_left = False
        elif key in [arcade.key.RIGHT, arcade.key.D]:
            self.turn_right = False

    def on_update(self, delta_time):
        if (
            not self.track.is_ontrack(
                self.car.center_x,
                self.car.center_y,
            )
            or self.out_of_track
        ):
            self.out_of_track = True
        else:
            if self.accelerate:
                self.physics_engine.apply_force(self.car, (0, ACCELERATE_FORCE))
            elif self.slowdown:
                if (
                    self.physics_engine.get_physics_object(self.car).body.velocity[1]
                    < BREAK_FORCE
                ):
                    self.physics_engine.set_velocity(self.car, (0, 0))
                else:
                    self.physics_engine.apply_force(self.car, (0, -BREAK_FORCE))
            if self.turn_left:
                self.physics_engine.get_physics_object(
                    self.car
                ).body.angle += CAR_TURN_SPEED
                self.physics_engine.set_velocity(
                    self.car,
                    self.physics_engine.get_physics_object(
                        self.car
                    ).body.velocity.rotated(
                        CAR_TURN_SPEED - CAR_DRIFT * CAR_TURN_SPEED
                    ),
                )
            elif self.turn_right:
                self.physics_engine.get_physics_object(
                    self.car
                ).body.angle -= CAR_TURN_SPEED
                self.physics_engine.set_velocity(
                    self.car,
                    self.physics_engine.get_physics_object(
                        self.car
                    ).body.velocity.rotated(
                        -(CAR_TURN_SPEED - CAR_DRIFT * CAR_TURN_SPEED)
                    ),
                )

        self.physics_engine.step()

    def on_draw(self):
        self.clear()
        self.scene.draw()
        # TODO DEBUG STUFF
        if self.out_of_track:
            oot_text = "On Track: No"
            oot_color = arcade.color.RED
        else:
            oot_text = "On Track: Yes"
            oot_color = arcade.color.WHITE
        arcade.draw_text(
            oot_text,
            start_x=1150,
            start_y=690,
            color=oot_color,
            bold=True,
            font_name="Roboto",
        )


def main():
    """Main method"""
    window = Racer()
    window.setup()
    arcade.run()


if __name__ == "__main__":
    main()
