# EcoCart AI 🌱

EcoCart AI is your intelligent companion for sustainable shopping and cooking. It helps reduce food waste and carbon footprint by tracking your fridge contents, suggesting recipes, and enabling smart shopping through Picnic integration.

## Features

- 🧊 Smart Fridge Management
- 🍳 Recipe Recommendations
- 📊 Sustainability Analysis
- 🛒 Picnic Shopping Integration
- 👆 MealSwiper Interface

## Setup

### Prerequisites

- Python 3.9+
- OpenAI API Key
- Chainlit
- LlamaIndex

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/EcoCart-AI.git
cd EcoCart-AI
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# Unix/MacOS
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the root directory with:
```env
OPENAI_API_KEY=your_api_key_here
```

### Project Structure

```
EcoCart-AI/
├── chatbot/
│   ├── app.py              # Main application
│   ├── components/         # UI components
│   ├── prompts/           # System prompts
│   │   ├── greeting.md
│   │   ├── fridge.md
│   │   └── analysis.md
│   └── public/            # Static assets
├── datasets/              # Recipe and sustainability data
└── requirements.txt       # Project dependencies
```

### Running the Application

1. Start the Chainlit server:
```bash
chainlit run chatbot/app.py
```

2. Open your browser and navigate to:
```
http://localhost:8000
```

## Usage

1. View Fridge Contents:
   - Ask "What's in my fridge?"
   - Get a list of items ordered by usage priority

2. Get Recipe Suggestions:
   - Ask for recipe recommendations
   - Use MealSwiper to browse and select recipes
   - View sustainability impact and cooking instructions

3. Shopping Integration:
   - Add missing ingredients to your Picnic cart
   - Get sustainable alternative suggestions

## Development

### Adding New Features

1. Update prompts in `chatbot/prompts/`
2. Modify UI components in `chatbot/components/`
3. Add new tools in `chatbot/app.py`

### Updating Data

1. Recipe database: `datasets/recipes.json`
2. Sustainability data: `datasets/sustainability_data.json`

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for GPT integration
- Chainlit for the chat interface
- LlamaIndex for data indexing
- Picnic for shopping integration 