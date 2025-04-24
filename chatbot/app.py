import os
from datetime import datetime
from json import load
from typing import List, Union

import chainlit as cl
import openai
from components.audio_handler import AudioHandler
from dotenv import load_dotenv
from llama_index.agent.openai import OpenAIAgent
from llama_index.core import (
    Document,
    PromptTemplate,
    Settings,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
    set_global_handler,
)
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.callbacks import CallbackManager
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.storage.chat_store import SimpleChatStore
from llama_index.core.tools import FunctionTool, QueryEngineTool, ToolMetadata
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from utils.recipe_extractor import RecipeExtractor


def load_or_build_index(data_path: Union[str, List[str]], index_name: str):
    if isinstance(data_path, List):
        json_data = []
        for path in data_path:
            with open(path, "r") as json_file:
                json_data += load(json_file)
    else:
        with open(data_path, "r") as json_file:
            json_data = load(json_file)

    documents = [Document(**i) for i in json_data]

    try:
        # rebuild storage context
        storage_context = StorageContext.from_defaults(
            persist_dir=f"./cache/{index_name}"
        )
        # load index
        index = load_index_from_storage(storage_context)
    except:
        index = VectorStoreIndex.from_documents(documents)
        index.storage_context.persist(f"./cache/{index_name}")

    return index


def read_prompt(path):
    with open(path) as prompt:
        return prompt.read()


VERBOSE_MODE = False
# set_global_handler("simple")
# Settings.callback_manager = CallbackManager([cl.LlamaIndexCallbackHandler()])

load_dotenv()
openai.api_key = os.environ.get("OPENAI_API_KEY")

Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-large")
Settings.context_window = 4096
TOP_K = 5

LLM = OpenAI(
    model="gpt-4o",
    temperature=0.7,
    max_tokens=1024,
    # streaming=True
)

# Initialize recipe extractor
recipe_extractor = RecipeExtractor(api_key=os.environ.get("OPENAI_API_KEY"))

# Initialize sustainability and recipe indices
sustainability_index = load_or_build_index(
    "datasets/sustainability_data.json", "sustainability"
)
recipe_index = load_or_build_index("datasets/recipes.json", "recipes")

sustainability_query_engine = sustainability_index.as_query_engine(
    llm=LLM,
    text_qa_template=PromptTemplate(read_prompt("prompts/sustainability_prompt.md")),
    similarity_top_k=TOP_K,
    verbose=VERBOSE_MODE,
)

recipe_query_engine = recipe_index.as_query_engine(
    llm=LLM,
    text_qa_template=PromptTemplate(read_prompt("prompts/recipe_prompt.md")),
    similarity_top_k=TOP_K,
    verbose=VERBOSE_MODE,
)

sustainability_tool = QueryEngineTool(
    sustainability_query_engine,
    ToolMetadata(
        description="Tool to get sustainability information about ingredients and cooking methods",
        name="sustainability_qa",
        return_direct=False,
    ),
)

recipe_tool = QueryEngineTool(
    recipe_query_engine,
    ToolMetadata(
        description="Tool to search and recommend recipes based on preferences and sustainability criteria",
        name="recipe_qa",
        return_direct=False,
    ),
)


# Tool definitions
def extract_recipe_from_url(url: str) -> dict:
    """Extract recipe information from a given URL."""
    return recipe_extractor.extract_recipe_from_url(url)


def calculate_sustainability_score(ingredients: List[dict]) -> dict:
    """Calculate sustainability score for given ingredients."""
    # This would connect to your sustainability calculation service
    return {
        "total_co2": sum([ing.get("co2", 0) for ing in ingredients]),
        "regional_percentage": sum(
            [1 for ing in ingredients if ing.get("is_local", False)]
        )
        / len(ingredients)
        * 100,
        "seasonal_percentage": sum(
            [1 for ing in ingredients if ing.get("is_seasonal", False)]
        )
        / len(ingredients)
        * 100,
        "plant_based_percentage": sum(
            [1 for ing in ingredients if ing.get("is_plant_based", True)]
        )
        / len(ingredients)
        * 100,
    }


def get_picnic_alternatives(ingredient: str) -> List[dict]:
    """Get sustainable alternatives from Picnic's catalog."""
    # This would connect to Picnic's API
    return [
        {"name": f"Bio {ingredient}", "co2": 0.5, "price": 2.99, "is_organic": True},
        {"name": f"Regional {ingredient}", "co2": 0.3, "price": 3.99, "is_local": True},
    ]


def get_recipe_recommendations(preferences: List[str]) -> List[dict]:
    """Get personalized recipe recommendations."""
    # This would connect to your recipe recommendation system
    return [
        {
            "title": "Veggie Pasta",
            "sustainability_score": 8.5,
            "matches_preferences": ["vegetarian", "quick"],
            "ingredients": ["pasta", "tomatoes", "basil"],
        },
        {
            "title": "Local Seasonal Salad",
            "sustainability_score": 9.0,
            "matches_preferences": ["local", "seasonal"],
            "ingredients": ["lettuce", "carrots", "apples"],
        },
    ]


def get_recipes_from_ingredients(ingredients: List[str]) -> List[dict]:
    """Find recipes that can be made with available ingredients and return top 5 matches."""
    matching_recipes = []

    # Ensure we have ingredients to work with
    if not ingredients or not isinstance(ingredients, list):
        return []

    # Clean and normalize ingredients
    available_ingredients = [ing.lower().strip() for ing in ingredients if ing]

    for recipe in recipe_index.get_documents():
        try:
            recipe_data = recipe.metadata
            recipe_ingredients = [
                ing["name"].lower().strip()
                for ing in recipe_data.get("ingredients", [])
            ]

            # Calculate matching ingredients
            matching_ingredients = set(recipe_ingredients) & set(available_ingredients)
            match_count = len(matching_ingredients)

            # Only consider recipes with at least one matching ingredient
            if match_count > 0:
                # Add recipe with match information
                missing_ingredients = set(recipe_ingredients) - set(
                    available_ingredients
                )
                recipe_info = {
                    "title": recipe_data.get("title", "Unnamed Recipe"),
                    "matching_ingredients": list(matching_ingredients),
                    "missing_ingredients": list(missing_ingredients),
                    "match_count": match_count,
                    "sustainability_score": recipe_data.get(
                        "sustainability_score", 5.0
                    ),
                    "image_url": recipe_data.get(
                        "image_url", "default_recipe_image.jpg"
                    ),
                    "preparation_time": recipe_data.get(
                        "preparation_time", "Not specified"
                    ),
                    "difficulty": recipe_data.get("difficulty", "Medium"),
                }
                matching_recipes.append(recipe_info)
        except Exception as e:
            continue  # Skip problematic recipes

    # Sort by number of matching ingredients and sustainability score
    matching_recipes.sort(
        key=lambda x: (x["match_count"], x["sustainability_score"]), reverse=True
    )

    # Return top 5 recipes
    return matching_recipes[:5]


def get_fridge_contents() -> List[dict]:
    """Get the current contents of the user's fridge with detailed sustainability metrics."""
    try:
        fridge_content = read_prompt("prompts/fridge.md")
        ingredients = []
        for line in fridge_content.strip().split("\n"):
            if line.strip():
                # Parse complex format: name (amount) [age] {risk} <co2>
                parts = line.split("(")
                name = parts[0].strip()

                # Extract amount
                amount = (
                    parts[1].split(")")[0].strip()
                    if len(parts) > 1
                    else "Not specified"
                )

                # Extract age
                age = (
                    line.split("[")[1].split("]")[0] if "[" in line else "Not specified"
                )

                # Extract risk
                risk_part = (
                    line.split("{")[1].split("}")[0] if "{" in line else "Not specified"
                )
                risk_level = risk_part.split()[0].strip()
                risk_percentage = (
                    risk_part.split()[2].strip("%")
                    if len(risk_part.split()) > 2
                    else "0"
                )

                # Extract CO2
                co2 = (
                    float(line.split("<")[1].split("CO2e>")[0].strip())
                    if "<" in line
                    else 0.0
                )

                ingredients.append(
                    {
                        "name": name,
                        "amount": amount,
                        "age": age,
                        "risk_level": risk_level,
                        "risk_percentage": float(risk_percentage),
                        "co2_impact": co2,
                    }
                )
        return ingredients
    except Exception as e:
        return []


def analyze_fridge_contents() -> dict:
    """Analyze fridge contents with focus on sustainability and CO2 impact."""
    try:
        fridge_contents = get_fridge_contents()

        # Calculate total CO2 at risk
        high_risk_items = [
            item for item in fridge_contents if item["risk_level"].lower() == "high"
        ]
        total_co2_at_risk = sum(item["co2_impact"] for item in high_risk_items)

        # Format items table
        items_table = ""
        for item in fridge_contents:
            items_table += f"{item['name']:<10} {item['risk_level']} ({item['risk_percentage']}%) {item['age']:<9} {float(item['amount'].split('kg')[0]):<10.2f} {item['co2_impact']:<10.2f}\n"

        # Generate priority actions
        priority_actions = []
        urgent_items = [
            item for item in high_risk_items if item["risk_percentage"] <= 5
        ]
        if urgent_items:
            priority_actions.append("Use these items TODAY:")
            for item in urgent_items:
                priority_actions.append(
                    f"- {item['name']} - less than 5% of shelf life remains!"
                )

        priority_actions.append("\nHigh-risk items to use soon:")
        for item in high_risk_items:
            if item not in urgent_items:
                priority_actions.append(
                    f"- {item['name']} ({item['risk_percentage']}% remaining)"
                )

        # Calculate driving equivalent (using 0.165 kg CO2 per km as conversion factor)
        driving_equivalent = round(total_co2_at_risk / 0.165, 1)

        # Get recipe suggestions based on available ingredients
        ingredient_names = [ing["name"] for ing in fridge_contents]
        recipes = get_recipes_from_ingredients(ingredient_names)

        # Format analysis template
        analysis_template = read_prompt("prompts/analysis.md")
        analysis = analysis_template.format(
            items_table=items_table,
            priority_actions="\n".join(priority_actions),
            total_co2=round(total_co2_at_risk, 2),
            driving_equivalent=driving_equivalent,
        )

        return {
            "analysis": analysis,
            "recipes": recipes,
            "high_risk_items": high_risk_items,
            "total_co2_at_risk": total_co2_at_risk,
            "driving_equivalent": driving_equivalent,
        }
    except Exception as e:
        return {"analysis": "Unable to analyze fridge contents", "recipes": []}


# Define tools list with our custom tools
tools = [
    FunctionTool(
        fn=get_recipes_from_ingredients,
        metadata=ToolMetadata(
            name="recipe_finder",
            description="Find recipes that can be made with given ingredients. Input should be a list of ingredient names.",
        ),
    ),
    FunctionTool(
        fn=get_fridge_contents,
        metadata=ToolMetadata(
            name="fridge_contents",
            description="Get the current contents of the user's fridge with amounts and expiry dates.",
        ),
    ),
    FunctionTool(
        fn=analyze_fridge_contents,
        metadata=ToolMetadata(
            name="fridge_analysis",
            description="Analyze fridge contents, suggest recipes, and highlight items that need to be used soon.",
        ),
    ),
    sustainability_tool,
    recipe_tool,
]

# Initialize audio handler
audio_handler = AudioHandler()


@cl.on_chat_start
async def start():
    # Set up the chat interface with logo and greeting
    greeting = read_prompt("prompts/greeting.md")
    await cl.Message(
        content=greeting,
        elements=[],
    ).send()

    # Initialize chat memory
    chat_store = SimpleChatStore()
    memory = ChatMemoryBuffer.from_defaults(
        chat_store=chat_store,
        token_limit=2000,
    )

    # Initialize agent
    agent = OpenAIAgent.from_tools(
        tools=[
            FunctionTool.from_defaults(fn=extract_recipe_from_url),
            FunctionTool.from_defaults(fn=calculate_sustainability_score),
            FunctionTool.from_defaults(fn=get_picnic_alternatives),
            FunctionTool.from_defaults(fn=get_recipe_recommendations),
            FunctionTool.from_defaults(fn=get_recipes_from_ingredients),
            sustainability_tool,
            recipe_tool,
        ],
        llm=LLM,
        memory=memory,
        system_prompt=read_prompt("prompts/agent_system_prompt.md"),
        verbose=VERBOSE_MODE,
    )

    cl.user_session.set("agent", agent)


@cl.on_message
async def main(message: cl.Message):
    agent = cl.user_session.get("agent")

    # Check if message contains audio
    if hasattr(message, "audio") and message.audio:
        # Process audio to text
        text = await audio_handler.process_audio(message.audio)
        if text:
            # Send transcription to user
            await cl.Message(content=f"🎤 Ich habe verstanden: {text}").send()
            # Update message content with transcribed text
            message.content = text
        else:
            return

    response = agent.chat(message.content)
    elements = []

    # Convert response to dictionary if it's not already
    response_data = {}
    if hasattr(response, "response"):
        if isinstance(response.response, dict):
            response_data = response.response
        else:
            # Send the text response directly if it's not a dictionary
            await cl.Message(content=str(response.response)).send()
            return

    if "fridge_contents" in response_data:
        # Create a formatted display of fridge contents
        content = "🧊 Your Fridge Contents:\n\n"
        for item in response_data["fridge_contents"]:
            content += (
                f"• {item['name']} ({item['amount']}) - Expires: {item['expiry']}\n"
            )
        await cl.Message(content=content).send()

    elif "fridge_analysis" in response_data:
        # Display fridge analysis and recipe suggestions
        content = "📊 Fridge Analysis:\n\n"
        content += response_data["analysis"] + "\n\n"

        if response_data.get("expiring_soon"):
            content += "⚠️ Items to use soon:\n"
            for item in response_data["expiring_soon"]:
                content += f"• {item['name']} ({item['amount']})\n"

        await cl.Message(content=content).send()

        # Display recipe suggestions if available
        if response_data.get("recipes"):
            await cl.Message(
                content="Here are some recipe suggestions based on your ingredients:"
            ).send()
            for recipe in response_data["recipes"]:
                elements.append(
                    cl.Card(
                        title=recipe["title"],
                        content=f"Matching ingredients: {', '.join(recipe['matching_ingredients'])}\nMissing ingredients: {', '.join(recipe['missing_ingredients'])}\nSustainability Score: {recipe['sustainability_score']}/10",
                        image_url=recipe.get("image_url", None),
                    )
                )
            await cl.Message(content="", elements=elements).send()

    elif "recipes" in response_data:
        for recipe in response_data["recipes"]:
            # Create card element for each recipe
            elements.append(
                cl.Card(
                    title=recipe["title"],
                    content=f"Matching ingredients: {', '.join(recipe['matching_ingredients'])}\nMissing ingredients: {', '.join(recipe['missing_ingredients'])}\nSustainability Score: {recipe['sustainability_score']}/10",
                    image_url=recipe.get("image_url", None),
                )
            )

        # Send the response with recipe cards
        await cl.Message(content=str(response.response), elements=elements).send()

        # Send swipe suggestion
        await cl.Message(
            content="👆 Swipe durch die Rezepte wie bei Tinder! Nach rechts wischen = Gefällt mir, nach links = Nächstes Rezept. Deine Likes werden für zukünftige Empfehlungen berücksichtigt. 🔄"
        ).send()

    elif response_data:  # If we have response data but no recipes
        await cl.Message(content=str(response_data)).send()
