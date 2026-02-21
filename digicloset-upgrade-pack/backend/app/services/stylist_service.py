import os
import base64
from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)

# Strict requirement to pick up the API key from environment variables
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    logger.warning("OPENROUTER_API_KEY is not set. Visual styling queries will fail.")

# Configure to hit OpenRouter using standard OpenAI SDK semantics
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

async def generate_cross_sell_query(image_bytes: bytes) -> str:
    """
    Passes an image to an OpenRouter vision model to generate a strictly textual query
    for a visually complementary garment.
    """
    try:
        # Encode image to base64 string
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        image_url = f"data:image/jpeg;base64,{base64_image}"
        
        # System prompt restricting output to basic keyword query
        system_prompt = (
            "You are an expert fashion stylist. I am giving you an image of a garment. "
            "Please recommend a visually complementary clothing item that would pair well with it "
            "to create a cohesive outfit (e.g. if I give a shirt, recommend pants or a jacket). "
            "IMPORTANT: Your response MUST be strictly limited to a concise 3-5 word search query "
            "describing the recommended item. Do NOT include any conversational filler, explanations, "
            "or punctuation. Example response: 'dark wash denim jeans' or 'beige knit cardigan'."
        )

        # We will use openrouter's free llama 3.2 vision instruct model
        response = await client.chat.completions.create(
            model="meta-llama/llama-3.2-11b-vision-instruct:free",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What is a single perfect complementary item for this?"},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ],
            temperature=0.7,
            max_tokens=20
        )
        
        query = response.choices[0].message.content.strip()
        logger.info(f"LLM Stylist recommended pair query: {query}")
        return query
        
    except Exception as e:
        logger.error(f"Error generating cross-sell query from LLM: {str(e)}")
        # If openrouter rate limits or fails, fallback to a safe neutral query
        return "black outfit accessory"
