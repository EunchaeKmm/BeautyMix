# BeautyMix
A Python-based makeup recommendation app that helps users create personalised looks using products they already own.


# BeautyMix

BeautyMix is a Python-based makeup collection and recommendation prototype built with Streamlit. It helps users explore makeup looks using products they already own, rather than relying on a fixed product catalogue.

Users can register makeup products, save product details and photos, choose a makeup vibe and context, and receive a suggested look with matching products from their own collection.

## Features

- **Product registration:** Save a product name, category, colour (where relevant), finish and optional photo.
- **My Collection:** View saved products, filter by category and remove products.
- **Personalised look selection:** Choose a makeup vibe, occasion, weather and available time. BeautyMix selects a compatible look and considers the occasion.
- **Product recommendations:** Match saved products using category, finish, colour palette, weather preferences and coordination with other selected products.
- **Finishing touches:** View optional styling suggestions for bronzer, highlighter, brows, lashes and contact lens colours.
- **Local data storage:** Save product details and recommendation history in JSON files.

## Technologies

- Python
- Streamlit
- JSON for local product and recommendation-history storage
- Python standard-library modules: `json`, `random`, `uuid`, `pathlib` and `urllib.parse`

## Project structure

```text
BeautyMix/
├── beautymix.py
├── requirements.txt
├── README.md
├── .gitignore
├── products.json          # created when products are saved; local user data
├── history.json           # created when recommendations are generated
├── uploads/               # uploaded product photos
└── assets/
    ├── logo.png           # optional BeautyMix logo
    └── looks/             # optional look inspiration images
```

The application creates the `uploads/` and `assets/looks/` folders when it runs. The `products.json` and `history.json` files are created as needed.

## Installation

Python 3.10 or later is recommended.

1. Download or clone this repository.
2. Open the project folder in Terminal.
3. (Recommended) Create and activate a virtual environment.

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows**
```bash
py -m venv .venv
.venv\Scripts\activate
```

4. Install dependencies:
```bash
python -m pip install -r requirements.txt
```

## Run the application

From the project folder, run:
```bash
python -m streamlit run beautymix.py
```

Open the local URL shown in Terminal (usually `http://localhost:8501`). To stop the app, press `Control + C` in Terminal.

## How to use

1. Open **Add a Product** and register makeup items. Photos are optional.
2. Open **My Collection** to view, filter or delete saved products.
3. Open **Create a Look**.
4. Select a makeup vibe, occasion, weather and available time.
5. Select **Recommend my products** to view the suggested look and products from your collection.

## How recommendations work

BeautyMix uses a rule-based recommendation approach:

- The selected vibe determines a pool of compatible makeup looks.
- The occasion influences the preferred look intensity.
- Recent look history reduces the chance of immediately repeating a look.
- Product finish and colour are compared with the selected look's preferences.
- Foundation finish is matched against the selected weather condition.
- Colour coordination between selected products can increase a product's score.
- Available time determines how many products may be selected from each category.

The recommendation score is a simple prototype score. It is not scientifically validated and should be treated as styling inspiration, not professional beauty advice.

## Current scope and limitations

- Product information is entered by the user. The current version does not automatically recognise products from photos.
- Recommendations use saved category, colour and finish information. The app does not analyse ingredients, skin type or actual skin undertone.
- Product and recommendation-history data are stored locally in JSON files and are not synchronised between devices.
- Look inspiration images are optional. If an image is not provided, the app displays a placeholder and a Pinterest inspiration link.

## Possible future improvements

Possible improvements include image-based product-category assistance, more detailed recommendation explanations, additional look inspiration images and more robust data management.

## Author

Created as a student prototype project.
