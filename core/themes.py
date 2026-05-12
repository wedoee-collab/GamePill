from dataclasses import dataclass


@dataclass(frozen=True)
class GameTheme:
    name: str
    primary: str       # hex — main accent (dot, separators, highlights)
    secondary: str     # hex — secondary text / badges
    bg_tint: tuple     # (r, g, b, a) — very subtle pill background tint
    live_color: str    # hex — LIVE dot (stays red for most, varies for some)


THEMES: dict[str, GameTheme] = {
    "valorant": GameTheme(
        name="Valorant",
        primary="#FF4655",
        secondary="#FF8A94",
        bg_tint=(255, 70, 85, 18),
        live_color="#FF4655",
    ),
    "league": GameTheme(
        name="League of Legends",
        primary="#C89B3C",
        secondary="#E8C56C",
        bg_tint=(200, 155, 60, 18),
        live_color="#C89B3C",
    ),
    "cs2": GameTheme(
        name="CS2",
        primary="#F0A500",
        secondary="#FFD040",
        bg_tint=(240, 165, 0, 18),
        live_color="#F0A500",
    ),
    "fortnite": GameTheme(
        name="Fortnite",
        primary="#00D4FF",
        secondary="#7B2FBE",
        bg_tint=(0, 212, 255, 18),
        live_color="#00D4FF",
    ),
    "minecraft": GameTheme(
        name="Minecraft",
        primary="#5DAD00",
        secondary="#8BCF40",
        bg_tint=(93, 173, 0, 18),
        live_color="#5DAD00",
    ),
    "apex": GameTheme(
        name="Apex Legends",
        primary="#DA292A",
        secondary="#FF6060",
        bg_tint=(218, 41, 42, 18),
        live_color="#DA292A",
    ),
    "gta": GameTheme(
        name="GTA V",
        primary="#F7941D",
        secondary="#FFB860",
        bg_tint=(247, 148, 29, 18),
        live_color="#F7941D",
    ),
    "overwatch": GameTheme(
        name="Overwatch 2",
        primary="#F99E1A",
        secondary="#FFFFFF",
        bg_tint=(249, 158, 26, 18),
        live_color="#F99E1A",
    ),
    "dota2": GameTheme(
        name="Dota 2",
        primary="#C8A84B",
        secondary="#C23C2A",
        bg_tint=(200, 168, 75, 18),
        live_color="#C23C2A",
    ),
    "rocket_league": GameTheme(
        name="Rocket League",
        primary="#1B9CE3",
        secondary="#70D0FF",
        bg_tint=(27, 156, 227, 18),
        live_color="#1B9CE3",
    ),
    "cod": GameTheme(
        name="Call of Duty",
        primary="#C0A060",
        secondary="#E0C080",
        bg_tint=(192, 160, 96, 18),
        live_color="#C0A060",
    ),
    "dbd": GameTheme(
        name="Dead by Daylight",
        primary="#CC4444",
        secondary="#FF8888",
        bg_tint=(139, 0, 0, 18),
        live_color="#CC4444",
    ),
    "hearthstone": GameTheme(
        name="Hearthstone",
        primary="#FFD700",
        secondary="#C8860A",
        bg_tint=(255, 215, 0, 18),
        live_color="#FFD700",
    ),
    "pubg": GameTheme(
        name="PUBG",
        primary="#F2A900",
        secondary="#E5C97E",
        bg_tint=(242, 169, 0, 18),
        live_color="#F2A900",
    ),
    "default": GameTheme(
        name="Gaming",
        primary="#ffffff",
        secondary="#aaaaaa",
        bg_tint=(255, 255, 255, 10),
        live_color="#ff3b30",
    ),
}
