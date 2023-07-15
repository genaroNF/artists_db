import seaborn as sns
import json


def main():
    palette = sns.color_palette("Spectral", 1474).as_hex()
    with open("palette.json", "w") as f:
        json.dump(palette, f)


main()