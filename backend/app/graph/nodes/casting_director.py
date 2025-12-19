"""
CastingDirector Node - Uses LLM to intelligently assign voices to characters.
"""
import json
from typing import Dict, Any, List
from uuid import uuid4

from app.graph.state import GraphState
from app.models import Cast, ProjectStatus
from app.database import get_session_context
from app.services.groq_service import groq_service
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Comprehensive list of available edge-tts voices for casting
AVAILABLE_VOICES = [
    # ==================== ENGLISH ====================
    # English - US
    {"voice_id": "en-US-AriaNeural", "name": "Aria", "gender": "Female", "locale": "en-US", "style": "warm, friendly narrator"},
    {"voice_id": "en-US-GuyNeural", "name": "Guy", "gender": "Male", "locale": "en-US", "style": "casual, conversational host"},
    {"voice_id": "en-US-JennyNeural", "name": "Jenny", "gender": "Female", "locale": "en-US", "style": "professional, clear expert"},
    {"voice_id": "en-US-DavisNeural", "name": "Davis", "gender": "Male", "locale": "en-US", "style": "authoritative, deep voice"},
    {"voice_id": "en-US-AmberNeural", "name": "Amber", "gender": "Female", "locale": "en-US", "style": "energetic, youthful"},
    {"voice_id": "en-US-AnaNeural", "name": "Ana", "gender": "Female", "locale": "en-US", "style": "young, curious student"},
    {"voice_id": "en-US-AndrewNeural", "name": "Andrew", "gender": "Male", "locale": "en-US", "style": "mature, trustworthy"},
    {"voice_id": "en-US-BrandonNeural", "name": "Brandon", "gender": "Male", "locale": "en-US", "style": "friendly, approachable"},
    {"voice_id": "en-US-ChristopherNeural", "name": "Christopher", "gender": "Male", "locale": "en-US", "style": "professional newscaster"},
    {"voice_id": "en-US-CoraNeural", "name": "Cora", "gender": "Female", "locale": "en-US", "style": "warm, motherly"},
    {"voice_id": "en-US-ElizabethNeural", "name": "Elizabeth", "gender": "Female", "locale": "en-US", "style": "sophisticated, elegant"},
    {"voice_id": "en-US-EricNeural", "name": "Eric", "gender": "Male", "locale": "en-US", "style": "youthful, dynamic"},
    {"voice_id": "en-US-JacobNeural", "name": "Jacob", "gender": "Male", "locale": "en-US", "style": "calm, reassuring"},
    {"voice_id": "en-US-JaneNeural", "name": "Jane", "gender": "Female", "locale": "en-US", "style": "friendly assistant"},
    {"voice_id": "en-US-JasonNeural", "name": "Jason", "gender": "Male", "locale": "en-US", "style": "energetic presenter"},
    {"voice_id": "en-US-MichelleNeural", "name": "Michelle", "gender": "Female", "locale": "en-US", "style": "professional, corporate"},
    {"voice_id": "en-US-MonicaNeural", "name": "Monica", "gender": "Female", "locale": "en-US", "style": "confident, articulate"},
    {"voice_id": "en-US-NancyNeural", "name": "Nancy", "gender": "Female", "locale": "en-US", "style": "news anchor"},
    {"voice_id": "en-US-RogerNeural", "name": "Roger", "gender": "Male", "locale": "en-US", "style": "wise, experienced mentor"},
    {"voice_id": "en-US-SaraNeural", "name": "Sara", "gender": "Female", "locale": "en-US", "style": "patient teacher"},
    {"voice_id": "en-US-SteffanNeural", "name": "Steffan", "gender": "Male", "locale": "en-US", "style": "enthusiastic presenter"},
    {"voice_id": "en-US-TonyNeural", "name": "Tony", "gender": "Male", "locale": "en-US", "style": "friendly comedian"},
    
    # English - UK
    {"voice_id": "en-GB-RyanNeural", "name": "Ryan", "gender": "Male", "locale": "en-GB", "style": "British, professional"},
    {"voice_id": "en-GB-SoniaNeural", "name": "Sonia", "gender": "Female", "locale": "en-GB", "style": "British, elegant"},
    {"voice_id": "en-GB-ThomasNeural", "name": "Thomas", "gender": "Male", "locale": "en-GB", "style": "British, authoritative"},
    {"voice_id": "en-GB-LibbyNeural", "name": "Libby", "gender": "Female", "locale": "en-GB", "style": "British, warm narrator"},
    {"voice_id": "en-GB-MaisieNeural", "name": "Maisie", "gender": "Female", "locale": "en-GB", "style": "British, young cheerful"},
    {"voice_id": "en-GB-AlfieNeural", "name": "Alfie", "gender": "Male", "locale": "en-GB", "style": "British, casual"},
    {"voice_id": "en-GB-BellaNeural", "name": "Bella", "gender": "Female", "locale": "en-GB", "style": "British, friendly"},
    {"voice_id": "en-GB-ElliotNeural", "name": "Elliot", "gender": "Male", "locale": "en-GB", "style": "British, professional"},
    {"voice_id": "en-GB-EthanNeural", "name": "Ethan", "gender": "Male", "locale": "en-GB", "style": "British, youthful"},
    {"voice_id": "en-GB-HollieNeural", "name": "Hollie", "gender": "Female", "locale": "en-GB", "style": "British, energetic"},
    {"voice_id": "en-GB-NoahNeural", "name": "Noah", "gender": "Male", "locale": "en-GB", "style": "British, calm"},
    {"voice_id": "en-GB-OliviaNeural", "name": "Olivia", "gender": "Female", "locale": "en-GB", "style": "British, sophisticated"},
    
    # English - Australia
    {"voice_id": "en-AU-NatashaNeural", "name": "Natasha", "gender": "Female", "locale": "en-AU", "style": "Australian, friendly"},
    {"voice_id": "en-AU-WilliamNeural", "name": "William", "gender": "Male", "locale": "en-AU", "style": "Australian, casual"},
    {"voice_id": "en-AU-AnnetteNeural", "name": "Annette", "gender": "Female", "locale": "en-AU", "style": "Australian, warm"},
    {"voice_id": "en-AU-CarlyNeural", "name": "Carly", "gender": "Female", "locale": "en-AU", "style": "Australian, energetic"},
    {"voice_id": "en-AU-DarrenNeural", "name": "Darren", "gender": "Male", "locale": "en-AU", "style": "Australian, relaxed"},
    {"voice_id": "en-AU-DuncanNeural", "name": "Duncan", "gender": "Male", "locale": "en-AU", "style": "Australian, authoritative"},
    {"voice_id": "en-AU-ElsieNeural", "name": "Elsie", "gender": "Female", "locale": "en-AU", "style": "Australian, cheerful"},
    # English - India
    {"voice_id": "en-IN-NeerjaNeural", "name": "Neerja", "gender": "Female", "locale": "en-IN", "style": "Indian English, clear"},
    {"voice_id": "en-IN-PrabhatNeural", "name": "Prabhat", "gender": "Male", "locale": "en-IN", "style": "Indian English, professional"},
    
    # English - Ireland
    {"voice_id": "en-IE-ConnorNeural", "name": "Connor", "gender": "Male", "locale": "en-IE", "style": "Irish, friendly"},
    {"voice_id": "en-IE-EmilyNeural", "name": "Emily", "gender": "Female", "locale": "en-IE", "style": "Irish, warm"},
    
    # English - Canada
    {"voice_id": "en-CA-ClaraNeural", "name": "Clara", "gender": "Female", "locale": "en-CA", "style": "Canadian, friendly"},
    {"voice_id": "en-CA-LiamNeural", "name": "Liam", "gender": "Male", "locale": "en-CA", "style": "Canadian, professional"},
    
    # English - New Zealand
    {"voice_id": "en-NZ-MitchellNeural", "name": "Mitchell", "gender": "Male", "locale": "en-NZ", "style": "New Zealand, casual"},
    {"voice_id": "en-NZ-MollyNeural", "name": "Molly", "gender": "Female", "locale": "en-NZ", "style": "New Zealand, friendly"},
    
    # English - Singapore
    {"voice_id": "en-SG-LunaNeural", "name": "Luna", "gender": "Female", "locale": "en-SG", "style": "Singaporean, clear"},
    {"voice_id": "en-SG-WayneNeural", "name": "Wayne", "gender": "Male", "locale": "en-SG", "style": "Singaporean, professional"},
    
    # English - South Africa
    {"voice_id": "en-ZA-LeahNeural", "name": "Leah", "gender": "Female", "locale": "en-ZA", "style": "South African, warm"},
    {"voice_id": "en-ZA-LukeNeural", "name": "Luke", "gender": "Male", "locale": "en-ZA", "style": "South African, friendly"},
    
    # English - Hong Kong
    {"voice_id": "en-HK-SamNeural", "name": "Sam", "gender": "Male", "locale": "en-HK", "style": "Hong Kong English, professional"},
    {"voice_id": "en-HK-YanNeural", "name": "Yan", "gender": "Female", "locale": "en-HK", "style": "Hong Kong English, clear"},
    
    # English - Kenya
    {"voice_id": "en-KE-AsiliaNeural", "name": "Asilia", "gender": "Female", "locale": "en-KE", "style": "Kenyan English, warm"},
    {"voice_id": "en-KE-ChilembaNeural", "name": "Chilemba", "gender": "Male", "locale": "en-KE", "style": "Kenyan English, friendly"},
    
    # English - Tanzania
    {"voice_id": "en-TZ-ElimuNeural", "name": "Elimu", "gender": "Male", "locale": "en-TZ", "style": "Tanzanian English, clear"},
    {"voice_id": "en-TZ-ImaniNeural", "name": "Imani", "gender": "Female", "locale": "en-TZ", "style": "Tanzanian English, warm"},
    
    # ==================== FILIPINO / TAGALOG ====================
    {"voice_id": "fil-PH-AngeloNeural", "name": "Angelo", "gender": "Male", "locale": "fil-PH", "style": "Filipino, friendly host"},
    {"voice_id": "fil-PH-BlessicaNeural", "name": "Blessica", "gender": "Female", "locale": "fil-PH", "style": "Filipino, warm and expressive"},
    
    # ==================== SPANISH ====================
    # Spanish - Spain
    {"voice_id": "es-ES-AlvaroNeural", "name": "Alvaro", "gender": "Male", "locale": "es-ES", "style": "Spanish, professional"},
    {"voice_id": "es-ES-ElviraNeural", "name": "Elvira", "gender": "Female", "locale": "es-ES", "style": "Spanish, elegant"},
    {"voice_id": "es-ES-AbrilNeural", "name": "Abril", "gender": "Female", "locale": "es-ES", "style": "Spanish, youthful"},

    # Spanish - Mexico
    {"voice_id": "es-MX-DaliaNeural", "name": "Dalia", "gender": "Female", "locale": "es-MX", "style": "Mexican, friendly"},
    {"voice_id": "es-MX-JorgeNeural", "name": "Jorge", "gender": "Male", "locale": "es-MX", "style": "Mexican, professional"},
    {"voice_id": "es-MX-BeatrizNeural", "name": "Beatriz", "gender": "Female", "locale": "es-MX", "style": "Mexican, warm"},

    # ==================== FRENCH ====================
    {"voice_id": "fr-FR-DeniseNeural", "name": "Denise", "gender": "Female", "locale": "fr-FR", "style": "French, elegant"},
    {"voice_id": "fr-FR-HenriNeural", "name": "Henri", "gender": "Male", "locale": "fr-FR", "style": "French, sophisticated"},
    {"voice_id": "fr-FR-AlainNeural", "name": "Alain", "gender": "Male", "locale": "fr-FR", "style": "French, professional"},

    # French - Canada
    {"voice_id": "fr-CA-AntoineNeural", "name": "Antoine", "gender": "Male", "locale": "fr-CA", "style": "Canadian French, friendly"},
    {"voice_id": "fr-CA-SylvieNeural", "name": "Sylvie", "gender": "Female", "locale": "fr-CA", "style": "Canadian French, warm"},
    {"voice_id": "fr-CA-JeanNeural", "name": "Jean", "gender": "Male", "locale": "fr-CA", "style": "Canadian French, professional"},

    # ==================== GERMAN ====================
    {"voice_id": "de-DE-KatjaNeural", "name": "Katja", "gender": "Female", "locale": "de-DE", "style": "German, professional"},
    {"voice_id": "de-DE-ConradNeural", "name": "Conrad", "gender": "Male", "locale": "de-DE", "style": "German, authoritative"},
    {"voice_id": "de-DE-AmalaNeural", "name": "Amala", "gender": "Female", "locale": "de-DE", "style": "German, friendly"},

    # ==================== JAPANESE ====================
    {"voice_id": "ja-JP-NanamiNeural", "name": "Nanami", "gender": "Female", "locale": "ja-JP", "style": "Japanese, professional"},
    {"voice_id": "ja-JP-KeitaNeural", "name": "Keita", "gender": "Male", "locale": "ja-JP", "style": "Japanese, friendly"},
    {"voice_id": "ja-JP-AoiNeural", "name": "Aoi", "gender": "Female", "locale": "ja-JP", "style": "Japanese, youthful"},

    # ==================== KOREAN ====================
    {"voice_id": "ko-KR-SunHiNeural", "name": "SunHi", "gender": "Female", "locale": "ko-KR", "style": "Korean, professional"},
    {"voice_id": "ko-KR-InJoonNeural", "name": "InJoon", "gender": "Male", "locale": "ko-KR", "style": "Korean, friendly"},
    {"voice_id": "ko-KR-BongJinNeural", "name": "BongJin", "gender": "Male", "locale": "ko-KR", "style": "Korean, calm"},

    # ==================== CHINESE ====================
    # Chinese - Mandarin (China)
    {"voice_id": "zh-CN-XiaoxiaoNeural", "name": "Xiaoxiao", "gender": "Female", "locale": "zh-CN", "style": "Chinese, warm friendly"},
    {"voice_id": "zh-CN-YunxiNeural", "name": "Yunxi", "gender": "Male", "locale": "zh-CN", "style": "Chinese, professional"},
    {"voice_id": "zh-CN-YunjianNeural", "name": "Yunjian", "gender": "Male", "locale": "zh-CN", "style": "Chinese, authoritative"},

    # Chinese - Taiwan
    {"voice_id": "zh-TW-HsiaoChenNeural", "name": "HsiaoChen", "gender": "Female", "locale": "zh-TW", "style": "Taiwanese, friendly"},
    {"voice_id": "zh-TW-YunJheNeural", "name": "YunJhe", "gender": "Male", "locale": "zh-TW", "style": "Taiwanese, professional"},
    {"voice_id": "zh-TW-HsiaoYuNeural", "name": "HsiaoYu", "gender": "Female", "locale": "zh-TW", "style": "Taiwanese, warm"},
    
    # Chinese - Hong Kong (Cantonese)
    {"voice_id": "zh-HK-HiuMaanNeural", "name": "HiuMaan", "gender": "Female", "locale": "zh-HK", "style": "Cantonese, professional"},
    {"voice_id": "zh-HK-WanLungNeural", "name": "WanLung", "gender": "Male", "locale": "zh-HK", "style": "Cantonese, authoritative"},
    {"voice_id": "zh-HK-HiuGaaiNeural", "name": "HiuGaai", "gender": "Female", "locale": "zh-HK", "style": "Cantonese, friendly"},
    
    # ==================== PORTUGUESE ====================
    # Portuguese - Brazil
    {"voice_id": "pt-BR-FranciscaNeural", "name": "Francisca", "gender": "Female", "locale": "pt-BR", "style": "Brazilian, warm"},
    {"voice_id": "pt-BR-AntonioNeural", "name": "Antonio", "gender": "Male", "locale": "pt-BR", "style": "Brazilian, professional"},
    {"voice_id": "pt-BR-BrendaNeural", "name": "Brenda", "gender": "Female", "locale": "pt-BR", "style": "Brazilian, youthful"},

    # Portuguese - Portugal
    {"voice_id": "pt-PT-DuarteNeural", "name": "Duarte", "gender": "Male", "locale": "pt-PT", "style": "Portuguese, professional"},
    {"voice_id": "pt-PT-RaquelNeural", "name": "Raquel", "gender": "Female", "locale": "pt-PT", "style": "Portuguese, elegant"},
    {"voice_id": "pt-PT-FernandaNeural", "name": "Fernanda", "gender": "Female", "locale": "pt-PT", "style": "Portuguese, warm"},
    
    # ==================== ITALIAN ====================
    {"voice_id": "it-IT-ElsaNeural", "name": "Elsa", "gender": "Female", "locale": "it-IT", "style": "Italian, elegant"},
    {"voice_id": "it-IT-DiegoNeural", "name": "Diego", "gender": "Male", "locale": "it-IT", "style": "Italian, professional"},
    {"voice_id": "it-IT-BenignoNeural", "name": "Benigno", "gender": "Male", "locale": "it-IT", "style": "Italian, friendly"},

    # ==================== RUSSIAN ====================
    {"voice_id": "ru-RU-SvetlanaNeural", "name": "Svetlana", "gender": "Female", "locale": "ru-RU", "style": "Russian, professional"},
    {"voice_id": "ru-RU-DmitryNeural", "name": "Dmitry", "gender": "Male", "locale": "ru-RU", "style": "Russian, authoritative"},
    {"voice_id": "ru-RU-DariyaNeural", "name": "Dariya", "gender": "Female", "locale": "ru-RU", "style": "Russian, warm"},
    
    # ==================== HINDI ====================
    {"voice_id": "hi-IN-SwaraNeural", "name": "Swara", "gender": "Female", "locale": "hi-IN", "style": "Hindi, professional"},
    {"voice_id": "hi-IN-MadhurNeural", "name": "Madhur", "gender": "Male", "locale": "hi-IN", "style": "Hindi, friendly"},
    
    # ==================== ARABIC ====================
    {"voice_id": "ar-SA-ZariyahNeural", "name": "Zariyah", "gender": "Female", "locale": "ar-SA", "style": "Arabic Saudi, professional"},
    {"voice_id": "ar-SA-HamedNeural", "name": "Hamed", "gender": "Male", "locale": "ar-SA", "style": "Arabic Saudi, authoritative"},
    {"voice_id": "ar-EG-SalmaNeural", "name": "Salma", "gender": "Female", "locale": "ar-EG", "style": "Arabic Egyptian, warm"},
    {"voice_id": "ar-EG-ShakirNeural", "name": "Shakir", "gender": "Male", "locale": "ar-EG", "style": "Arabic Egyptian, friendly"},
    
    # ==================== DUTCH ====================
    {"voice_id": "nl-NL-ColetteNeural", "name": "Colette", "gender": "Female", "locale": "nl-NL", "style": "Dutch, professional"},
    {"voice_id": "nl-NL-MaartenNeural", "name": "Maarten", "gender": "Male", "locale": "nl-NL", "style": "Dutch, friendly"},
    {"voice_id": "nl-NL-FennaNeural", "name": "Fenna", "gender": "Female", "locale": "nl-NL", "style": "Dutch, warm"},
    
    # ==================== POLISH ====================
    {"voice_id": "pl-PL-AgnieszkaNeural", "name": "Agnieszka", "gender": "Female", "locale": "pl-PL", "style": "Polish, professional"},
    {"voice_id": "pl-PL-MarekNeural", "name": "Marek", "gender": "Male", "locale": "pl-PL", "style": "Polish, authoritative"},
    {"voice_id": "pl-PL-ZofiaNeural", "name": "Zofia", "gender": "Female", "locale": "pl-PL", "style": "Polish, warm"},
    
    # ==================== SWEDISH ====================
    {"voice_id": "sv-SE-SofieNeural", "name": "Sofie", "gender": "Female", "locale": "sv-SE", "style": "Swedish, professional"},
    {"voice_id": "sv-SE-MattiasNeural", "name": "Mattias", "gender": "Male", "locale": "sv-SE", "style": "Swedish, friendly"},
    {"voice_id": "sv-SE-HilleviNeural", "name": "Hillevi", "gender": "Female", "locale": "sv-SE", "style": "Swedish, warm"},
    
    # ==================== THAI ====================
    {"voice_id": "th-TH-PremwadeeNeural", "name": "Premwadee", "gender": "Female", "locale": "th-TH", "style": "Thai, professional"},
    {"voice_id": "th-TH-NiwatNeural", "name": "Niwat", "gender": "Male", "locale": "th-TH", "style": "Thai, friendly"},
    {"voice_id": "th-TH-AcharaNeural", "name": "Achara", "gender": "Female", "locale": "th-TH", "style": "Thai, warm"},
    
    # ==================== VIETNAMESE ====================
    {"voice_id": "vi-VN-HoaiMyNeural", "name": "HoaiMy", "gender": "Female", "locale": "vi-VN", "style": "Vietnamese, professional"},
    {"voice_id": "vi-VN-NamMinhNeural", "name": "NamMinh", "gender": "Male", "locale": "vi-VN", "style": "Vietnamese, friendly"},
    
    # ==================== INDONESIAN ====================
    {"voice_id": "id-ID-GadisNeural", "name": "Gadis", "gender": "Female", "locale": "id-ID", "style": "Indonesian, professional"},
    {"voice_id": "id-ID-ArdiNeural", "name": "Ardi", "gender": "Male", "locale": "id-ID", "style": "Indonesian, friendly"},
    
    # ==================== MALAY ====================
    {"voice_id": "ms-MY-YasminNeural", "name": "Yasmin", "gender": "Female", "locale": "ms-MY", "style": "Malay, professional"},
    {"voice_id": "ms-MY-OsmanNeural", "name": "Osman", "gender": "Male", "locale": "ms-MY", "style": "Malay, friendly"},
    
    # ==================== TURKISH ====================
    {"voice_id": "tr-TR-EmelNeural", "name": "Emel", "gender": "Female", "locale": "tr-TR", "style": "Turkish, professional"},
    {"voice_id": "tr-TR-AhmetNeural", "name": "Ahmet", "gender": "Male", "locale": "tr-TR", "style": "Turkish, authoritative"},
]


# Fallback voices if LLM fails
FALLBACK_VOICES = [
    {"voice_id": "en-US-GuyNeural", "pitch": "+0Hz", "rate": "+0%"},
    {"voice_id": "en-US-AriaNeural", "pitch": "+0Hz", "rate": "+0%"},
    {"voice_id": "en-US-DavisNeural", "pitch": "+0Hz", "rate": "+0%"},
    {"voice_id": "en-US-JennyNeural", "pitch": "+0Hz", "rate": "+0%"},
]


async def casting_director_node(state: GraphState) -> GraphState:
    """
    Use LLM to intelligently assign voices to each character.
    
    Analyzes character names, dialogue content, and personality to select
    the most appropriate voice from available options.
    """
    logger.info("CastingDirector node started", project_id=state["project_id"])
    
    state["current_step"] = "casting"
    
    try:
        script_json = state["script_json"]
        scenes = script_json.get("scenes", [])
        
        # Extract unique speakers with their dialogue
        speaker_data = {}
        for scene in scenes:
            speaker = scene["speaker"]
            if speaker not in speaker_data:
                speaker_data[speaker] = []
            speaker_data[speaker].append(scene["line"])
        
        # Use LLM to select voices
        cast_assignments = await _llm_select_voices(speaker_data)
        
        # If LLM fails, use fallback
        if not cast_assignments:
            cast_assignments = _fallback_casting(list(speaker_data.keys()))
        
        # Save to database
        async with get_session_context() as session:
            from app.models import Project
            from uuid import UUID as UUIDType
            
            project = await session.get(Project, UUIDType(state["project_id"]))
            if project:
                project.status = ProjectStatus.GENERATING_AUDIO
                session.add(project)
            
            cast = Cast(
                id=uuid4(),
                project_id=state["project_id"],
                assignments=cast_assignments
            )
            session.add(cast)
            await session.commit()
        
        state["cast_list"] = cast_assignments
        state["progress"] = 0.3
        
        logger.info(
            "LLM casting completed",
            project_id=state["project_id"],
            characters=list(cast_assignments.keys())
        )
        
    except Exception as e:
        error_msg = f"Casting failed: {str(e)}"
        logger.error(error_msg, project_id=state["project_id"])
        state["errors"].append(error_msg)
        
        # Use fallback
        speakers = list(set(
            scene["speaker"] for scene in state["script_json"].get("scenes", [])
        ))
        state["cast_list"] = _fallback_casting(speakers)
    
    return state


async def _llm_select_voices(speaker_data: Dict[str, List[str]]) -> Dict[str, Dict[str, str]]:
    """
    Use Groq LLM to intelligently select voices for each character.
    """
    # Build voice options summary for the prompt
    voice_options = "\n".join([
        f"- {v['voice_id']}: {v['name']} ({v['gender']}, {v['locale']}) - {v['style']}"
        for v in AVAILABLE_VOICES
    ])
    
    # Build character summary
    character_summaries = []
    for speaker, lines in speaker_data.items():
        sample_lines = lines[:3]  # First 3 lines as sample
        character_summaries.append(
            f"Character: {speaker}\nSample dialogue:\n" + 
            "\n".join(f'  "{line}"' for line in sample_lines)
        )
    
    prompt = f"""You are a professional voice casting director. Analyze these characters and their dialogue, then assign the most appropriate voice from the available options.

AVAILABLE VOICES:
{voice_options}

CHARACTERS TO CAST:
{chr(10).join(character_summaries)}

For each character, select a voice that matches:
1. The character's apparent personality based on their name and dialogue
2. The tone and style of their speech
3. Ensure voice variety - don't assign the same voice to multiple characters

Also suggest pitch and rate adjustments:
- pitch: from -10Hz to +10Hz (negative = deeper, positive = higher)
- rate: from -20% to +30% (negative = slower, positive = faster)

Respond with ONLY a valid JSON object in this exact format (no markdown):
{{
  "CharacterName": {{
    "voice_id": "exact-voice-id-from-list",
    "pitch": "+0Hz",
    "rate": "+0%",
    "reasoning": "brief explanation"
  }}
}}
"""

    try:
        response = await groq_service.generate_raw(prompt)
        
        # Clean response - remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        response = response.strip()
        
        casting_data = json.loads(response)
        
        # Validate and extract assignments
        assignments = {}
        used_voices = set()
        
        for character, data in casting_data.items():
            voice_id = data.get("voice_id", "")
            
            # Validate voice exists
            valid_ids = [v["voice_id"] for v in AVAILABLE_VOICES]
            if voice_id not in valid_ids:
                # Find closest match or use fallback
                voice_id = FALLBACK_VOICES[len(assignments) % len(FALLBACK_VOICES)]["voice_id"]
            
            # Ensure no duplicate voices
            if voice_id in used_voices:
                for fallback in AVAILABLE_VOICES:
                    if fallback["voice_id"] not in used_voices:
                        voice_id = fallback["voice_id"]
                        break
            
            used_voices.add(voice_id)
            
            assignments[character] = {
                "voice_id": voice_id,
                "pitch": data.get("pitch", "+0Hz"),
                "rate": data.get("rate", "+0%")
            }
        
        return assignments
        
    except Exception as e:
        logger.error("LLM voice selection failed", error=str(e))
        return {}


def _fallback_casting(speakers: List[str]) -> Dict[str, Dict[str, str]]:
    """Fallback casting when LLM fails."""
    assignments = {}
    for i, speaker in enumerate(speakers):
        voice = FALLBACK_VOICES[i % len(FALLBACK_VOICES)]
        assignments[speaker] = voice.copy()
    return assignments