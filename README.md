# BeautyMix

BeautyMix is a Python and Streamlit prototype that recommends a makeup look using **only the products you already own**. Instead of pushing new purchases, it helps users rediscover how to combine the foundation, blush, eyeshadow and lip products already in their collection.

It was built for the Creative Coding A2 Code Prototype Project. The focus is the recommendation logic: how product data (category, colour, finish) and context (vibe, occasion, weather, time) are turned into a look.


## Features

- **Add a Product:** save a name, category, finish and optional photo. Colour is chosen for Blush, Eyeshadow and Lip (Foundation has no colour). Colours can be typed in freely, and an eyeshadow palette can hold several colours.
- **My Collection:** browse products as cards, filter by category, and open the `⋮` menu on a card to edit a product (including replacing its photo) or delete it.
- **Create a Look:** choose a makeup vibe (or Surprise Me), occasion, weather and available time. BeautyMix picks a look from a library of ten and recommends products from your own collection.
- **Results:** the look name, description and illustration; products grouped by category in application order; layering and placement notes; short reasons for every product; and warm or cool finishing touches (bronzer, highlighter, brows, contact lenses, lashes).
- **Mood board (optional):** your own photos of the look are pinned top-right while you read the results. Use the arrows on the photo to switch between them.
- **Local storage:** products and recommendation history are saved in JSON files, and photos are saved in `uploads/`, so they persist between sessions.

## Requirements

- Python 3.10 or later
- Streamlit (a recent version: the code uses `st.dialog`, keyed containers and `st.image(width="stretch")`)
- Pillow is installed together with Streamlit and is used only to check that mood-board images can be opened

Tested with: Python `[x.y.z]` and Streamlit `[x.y.z]` (check with `python --version` and `pip show streamlit`).

## Project structure

```text
BeautyMix/
├── beautymix.py                  # the whole application
├── requirements.txt
├── README.md
├── .gitignore
├── products.json                 # created when you save a product (your data)
├── recommendation_history.json   # created when you generate a look
├── uploads/                      # your uploaded product photos
└── assets/
    ├── beautymix_logo.png        # logo shown at the top
    ├── looks/                    # one illustration per look, e.g. clean_girl.png
    └── my_looks/                 # optional: your own look photos (mood board)
```

`uploads/`, `assets/looks/` and `assets/my_looks/` are created automatically if missing.

## Installation

1. Download or clone this repository and open the folder in a terminal.
2. (Recommended) create a virtual environment.

   macOS / Linux:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
   Windows:
   ```bash
   py -m venv .venv
   .venv\Scripts\activate
   ```
3. Install the dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```

## Run

```bash
python -m streamlit run beautymix.py
```

Open the local address printed in the terminal (usually `http://localhost:8501`). Stop the app with `Ctrl + C`.

## Quick try

The repository contains no personal data, so add a few products first:

1. Open **Add a Product** and add at least one item in each category (Foundation, Blush, Eyeshadow, Lip). Photos are optional.
2. Open **Create a Look**, choose a vibe, occasion, weather and time, then press **Create my BeautyMix look**.
3. To use the mood board, copy photos into `assets/my_looks/` named after the look: `clean_girl.jpg` is photo 1, `clean_girl_2.png` is photo 2, `clean_girl_3.jpg` is photo 3.

## How recommendations work

BeautyMix is a rule-based (knowledge-based) recommender. Nothing is learned from data; every rule is written in `beautymix.py`.

- The chosen **vibe** gives a pool of looks, and the **occasion** decides how bold the look should be. Recent looks are less likely to repeat (`recommendation_history.json`).
- Heavy looks (Baddie Glam, Icy Glam) only appear for 20 or 30 minutes and for Date, Party or Special Event.
- Each product is **scored** on its finish, its colour group and the look's colour story. Weather changes the foundation choice only: matte for hot and humid, glowy for cold and dry, natural for mild. Blush is not changed by weather.
- **Colour classification:** a typed colour such as "Peach Beige" is grouped by its last recognised base colour (Beige). Unknown names are kept as typed.
- **Coordination:** colours that match products already chosen get a bonus, and only one glitter product is encouraged per look.
- **Time:** foundation is always 1 product. 10 minutes gives 1 product per category; 20 minutes gives 1–2 blush, eyeshadow and lip; 30 minutes gives 2 blush, 2–4 eyeshadow and 2–4 lip. A palette counts as one product.
- **Ties** are broken by what was not recommended recently, then randomly.
- **Layering:** inside a category, matte goes first and shiny finishes last; products with the same finish go from light to deep. At most two shiny lip products are recommended together.
- **Look rules:** Bold Lip uses a red lip with nude blush and eyeshadow; Monochromatic Makeup repeats one colour family and also suggests using the blush on the eyes.
- Categories you do not own are skipped, with a message.
- The score is a simple prototype score. It is not scientifically validated and is styling inspiration, not professional beauty advice.

## Limitations

- Product details are typed in by the user. Products are not recognised from photos.
- Only saved category, colour and finish are used. The app does not consider skin type, ingredients or real skin undertone; warm and cool suggestions are styling inspiration only.
- Weights and colour groups (for example, red is treated as cool) are the author's own design decisions.
- Data is stored locally and is not synchronised between devices.

## Future improvements

- Help with product category from a photo (an early plan that was dropped to keep the project focused on recommendation).
- Learn from user ratings to improve recommendations.
- Compress uploaded images and refactor products into a class.

## Acknowledgements and Use of GenAI

- Built using Python and [Streamlit](https://streamlit.io).
- Standard-library modules used include `collections`, `html`, `json`, `random`, `re`, `uuid`, `pathlib` and `urllib.parse`.
- Claude (Anthropic, 2026) was used as a generative AI tool to assist with debugging and exploring possible solutions during development. All suggested changes were reviewed and tested by the author.


## Author

Eunchae Kim, 14642918, Creative Coding, University of Technology Sydney (A2 Code Prototype Project, 2026).
