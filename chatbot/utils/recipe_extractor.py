import json
import logging
import re
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from openai import OpenAI


class RecipeExtractor:
    def __init__(self, api_key: str):
        """Initialize the RecipeExtractor with OpenAI API key."""
        self.client = OpenAI(api_key=api_key)
        self.supported_domains = {
            "chefkoch.de": self._extract_chefkoch,
            "kitchenstories.com": self._extract_kitchenstories,
            # Add more supported domains here
        }

    def extract_recipe_from_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract recipe information from a given URL."""
        try:
            # First try normal extraction
            recipe_info = self._extract_from_webpage(url)
            if recipe_info:
                return recipe_info

            # If that fails, try intelligent URL analysis
            return self._analyze_recipe_url(url)

        except Exception as e:
            logging.error(f"Error extracting recipe: {str(e)}")
            # Fallback to URL analysis
            return self._analyze_recipe_url(url)

    def _analyze_recipe_url(self, url: str) -> Optional[Dict]:
        """Analyzes the URL structure to make educated guesses about the recipe."""
        try:
            # Extract recipe name from URL
            if "chefkoch.de/rezepte/" in url:
                # Extract recipe name from Chefkoch URL
                recipe_name = url.split("/")[-1]
                # Remove ID and clean up
                recipe_name = re.sub(r"^\d+\/", "", recipe_name)
                recipe_name = recipe_name.replace("-", " ").replace(".html", "")

                return {
                    "title": recipe_name.title(),
                    "source": "Chefkoch.de",
                    "url": url,
                    "note": "⚠️ Dies ist eine geschätzte Interpretation basierend auf der URL, da das Rezept nicht direkt zugänglich war.",
                    "estimated": True,
                }

        except Exception as e:
            logging.error(f"Error analyzing recipe URL: {str(e)}")
            return None

    def _extract_from_webpage(self, url: str) -> Optional[Dict]:
        """Original webpage extraction logic."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            # ... rest of extraction logic ...

        except Exception as e:
            logging.error(f"Error in webpage extraction: {str(e)}")
            return None

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        return url.split("//")[-1].split("/")[0]

    def _extract_chefkoch(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract recipe from Chefkoch.de."""
        try:
            # Extract recipe schema JSON
            script = soup.find("script", {"type": "application/ld+json"})
            if script:
                data = json.loads(script.string)
                return {
                    "title": data.get("name", ""),
                    "ingredients": [
                        {
                            "name": item["name"],
                            "amount": item.get("amount", ""),
                            "unit": item.get("unitOfMeasurement", ""),
                        }
                        for item in data.get("recipeIngredient", [])
                    ],
                    "instructions": data.get("recipeInstructions", []),
                    "servings": data.get("recipeYield", ""),
                    "prep_time": data.get("prepTime", ""),
                    "cook_time": data.get("cookTime", ""),
                    "image_url": data.get("image", {}).get("url", ""),
                    "source": "chefkoch.de",
                }
            raise ValueError("No recipe schema found")
        except Exception as e:
            print(f"Error extracting from Chefkoch: {str(e)}")
            return self._extract_with_ai(soup)

    def _extract_kitchenstories(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract recipe from KitchenStories."""
        # Implementation for Kitchen Stories
        # Similar to Chefkoch but with different selectors
        pass

    def _extract_with_ai(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract recipe using AI when structured data is not available."""
        # Clean the HTML content
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()

        text = soup.get_text(separator="\n", strip=True)

        prompt = f"""
        Extract recipe information from the following webpage content. 
        Return a JSON object with the following structure:
        {{
            "title": "Recipe title",
            "ingredients": [
                {{"name": "ingredient name", "amount": "amount", "unit": "unit"}}
            ],
            "instructions": ["step 1", "step 2", ...],
            "servings": "number of servings",
            "prep_time": "preparation time",
            "cook_time": "cooking time"
        }}

        Webpage content:
        {text[:4000]}
        """

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            response_format={"type": "json"},
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that extracts recipe information from webpages and returns it in JSON format.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        return json.loads(response.choices[0].message.content)

    def _enhance_recipe_data(self, recipe_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance recipe data with sustainability information."""
        if not recipe_data or "ingredients" not in recipe_data:
            return recipe_data

        # Calculate sustainability metrics for each ingredient
        for ingredient in recipe_data["ingredients"]:
            sustainability_info = self._get_ingredient_sustainability(
                ingredient["name"]
            )
            ingredient.update(sustainability_info)

        # Calculate overall recipe sustainability
        total_ingredients = len(recipe_data["ingredients"])
        if total_ingredients > 0:
            recipe_data["sustainability_metrics"] = {
                "co2_score": sum(
                    ing.get("co2_score", 0) for ing in recipe_data["ingredients"]
                )
                / total_ingredients,
                "water_usage": sum(
                    ing.get("water_usage", 0) for ing in recipe_data["ingredients"]
                )
                / total_ingredients,
                "seasonal": sum(
                    1
                    for ing in recipe_data["ingredients"]
                    if ing.get("is_seasonal", False)
                )
                / total_ingredients
                * 100,
                "local": sum(
                    1
                    for ing in recipe_data["ingredients"]
                    if ing.get("is_local", False)
                )
                / total_ingredients
                * 100,
            }

        return recipe_data

    def _get_ingredient_sustainability(self, ingredient_name: str) -> Dict[str, Any]:
        """Get sustainability information for an ingredient."""
        # This would connect to a sustainability database
        # For now, return dummy data
        return {
            "co2_score": 5.0,  # Scale 1-10, lower is better
            "water_usage": 100,  # Liters per kg
            "is_seasonal": True,
            "is_local": True,
            "alternatives": [
                {
                    "name": f"Sustainable {ingredient_name}",
                    "co2_score": 3.0,
                    "reason": "Locally sourced",
                }
            ],
        }

    def format_recipe_for_display(self, recipe_data: Dict[str, Any]) -> str:
        """Format recipe data for user display."""
        if not recipe_data:
            return "Could not extract recipe information."

        output = []
        output.append(f"🍳 {recipe_data['title']}\n")

        if "servings" in recipe_data:
            output.append(f"👥 Serves: {recipe_data['servings']}")
        if "prep_time" in recipe_data:
            output.append(f"⏲️ Prep Time: {recipe_data['prep_time']}")
        if "cook_time" in recipe_data:
            output.append(f"⏰ Cook Time: {recipe_data['cook_time']}")
        output.append("")

        output.append("📝 Ingredients:")
        for ing in recipe_data["ingredients"]:
            amount = ing.get("amount", "")
            unit = ing.get("unit", "")
            name = ing.get("name", "")
            output.append(f"- {amount} {unit} {name}")
        output.append("")

        if "instructions" in recipe_data:
            output.append("👩‍🍳 Instructions:")
            for i, step in enumerate(recipe_data["instructions"], 1):
                output.append(f"{i}. {step}")
            output.append("")

        if "sustainability_metrics" in recipe_data:
            metrics = recipe_data["sustainability_metrics"]
            output.append("🌱 Sustainability Metrics:")
            output.append(f"- CO2 Score: {metrics['co2_score']:.1f}/10")
            output.append(f"- Water Usage: {metrics['water_usage']:.0f}L/kg")
            output.append(f"- Seasonal Ingredients: {metrics['seasonal']:.0f}%")
            output.append(f"- Local Ingredients: {metrics['local']:.0f}%")

        return "\n".join(output)

    def format_recipe_for_analysis(self, recipe_info: Dict) -> str:
        """Formats the recipe information into a string for analysis."""
        if not recipe_info:
            return "Rezept konnte nicht extrahiert werden."

        if recipe_info.get("estimated", False):
            # Analyze based on recipe name
            title = recipe_info["title"]

            # Extract key components from title
            components = title.lower().split()

            # Basic recipe analysis
            return f"""
Rezept: {title}
Quelle: {recipe_info['source']}

Basierend auf dem Rezeptnamen handelt es sich um einen {components[0]}.
Besondere Merkmale: {', '.join(components[1:])}

Empfohlene Beilagen:
- Kartoffelknödel
- Rotkohl
- Semmelknödel

Geschätzte Zubereitungszeit: 2-3 Stunden
Schwierigkeitsgrad: Mittel

Nachhaltigkeits-Tipps:
- Fleisch vom lokalen Metzger verwenden
- Saisonales Gemüse als Beilage wählen
- Reste können gut eingefroren werden
"""

        # Normal recipe formatting
        return f"""
Rezept: {recipe_info.get('title', 'Unbekannt')}
Quelle: {recipe_info.get('source', 'Unbekannt')}
Portionen: {recipe_info.get('servings', 'Nicht angegeben')}

Zutaten:
{recipe_info.get('ingredients', 'Keine Zutaten verfügbar')}

Anleitung:
{recipe_info.get('instructions', 'Keine Anleitung verfügbar')}
"""
