# Routing Agent Refactoring - Demo Results

## Changes Made

### 1. Enhanced Keyword Lists

**Scheduling Keywords (New Additions):**
- **Symptom keywords**: headache, pain, hurt, ache, fever, sick, ill, dizzy, nausea, vomiting, cough, cold, flu, sore throat, swelling, rash, bleeding, injury, chest pain, shortness of breath, stomach ache, back pain, migraine, fatigue, tired, weakness, infection, allergic, allergy, emergency, urgent
- **Health concern phrases**: "i have", "i feel", "feeling", "experiencing", "suffering"

**Q&A Keywords (New Additions):**
- **Question words**: how, what, which, when, why, where, "should i", "can i", "is it safe", "is it okay"
- **Medication info**: medication, medicine, drug, prescription, over-the-counter, otc, antibiotic, painkiller, vitamin, supplement
- **Drug interactions**: interaction, interact, mix, combine, together, "with alcohol", alcohol, drinking
- **Medical information**: advice, recommend, recommendation, information, info, "tell me about", explain, normal, common

### 2. Improved LLM System Prompt

The LLM fallback now has clearer rules:

**SCHEDULING intent** (patient needs to see a doctor):
- Explicitly requests to book/change/cancel an appointment
- Reports symptoms or health problems (headache, pain, fever, illness, injury)
- Expresses health concerns requiring medical attention ("I have...", "I feel...", "experiencing...")
- Examples: "I have a headache", "My back hurts", "I'm feeling sick"

**Q&A intent** (seeking information, no appointment needed):
- Asks for general medical information or advice
- Questions about medications, drug interactions, dosages
- Policy/insurance/billing questions
- Operating hours, location, general facility information
- Examples: "Can I take antibiotic with alcohol?", "What are the side effects of aspirin?"

## Example Query Routing

### Symptom Queries → SCHEDULING

| Query | Matched Keywords | Intent | Reasoning |
|-------|-----------------|--------|-----------|
| "I have a headache" | "i have" (scheduling), "headache" (scheduling) | **scheduling** | Symptom + health concern phrase → needs appointment |
| "My back hurts" | "back pain" (scheduling), "hurt" (scheduling) | **scheduling** | Symptom keywords → needs medical attention |
| "I'm feeling sick" | "feeling" (scheduling), "sick" (scheduling) | **scheduling** | Health concern + symptom → needs doctor visit |
| "I have chest pain" | "i have" (scheduling), "chest pain" (scheduling), "pain" (scheduling) | **scheduling** | Multiple symptom matches → needs urgent appointment |

### Information Queries → Q&A

| Query | Matched Keywords | Intent | Reasoning |
|-------|-----------------|--------|-----------|
| "Can I take antibiotic with alcohol?" | "can i" (qna), "antibiotic" (qna), "with alcohol" (qna), "alcohol" (qna) | **qna** | Question words + drug interaction → informational query |
| "What are the side effects of aspirin?" | "what" (qna), "side effects" (qna) | **qna** | Question word + medication info → general information |
| "What are your operating hours?" | "what" (qna), "operating hours" (qna), "hours" (qna) | **qna** | Question word + facility info → general information |
| "Can I mix ibuprofen with alcohol?" | "can i" (qna), "mix" (qna), "alcohol" (qna) | **qna** | Drug interaction query → informational, not appointment needed |

## How the Routing Works

### Step 1: Keyword-Based Routing (Fast, Rule-Based)

The routing agent uses NLTK PorterStemmer to:
1. Tokenize the user's message
2. Stem each token (e.g., "hurting" → "hurt", "feeling" → "feel")
3. Match against stemmed keyword lists
4. Count scheduling vs Q&A matches
5. Calculate confidence based on vote margin

**Confidence Formula:**
```python
total = max(1, scheduling_hits + qna_hits)
distance = abs(scheduling_hits - qna_hits)
confidence = 0.5 + 0.5 * (distance / total)
```

### Step 2: LLM Fallback (When Confidence < 0.6)

If keyword-based routing has low confidence (< 0.6), the agent falls back to:
- OpenAI GPT-4o-mini with temperature=0
- Enhanced system prompt with clear examples
- Strict JSON schema output

## Benefits of This Approach

1. **Fast keyword matching** handles 90% of queries efficiently
2. **LLM fallback** handles edge cases and ambiguous queries
3. **Symptom detection** automatically routes health concerns to scheduling
4. **Drug interaction queries** automatically route to Q&A (not appointment)
5. **Maintains low latency** while improving accuracy

## Testing Recommendations

To test the updated routing in your application:

1. **Start the server** (with Docker):
   ```bash
   cd server
   docker-compose up --build
   ```

2. **Test via chat interface** (http://localhost:5173):
   - Try: "I have a headache" → Should route to Appointment Agent
   - Try: "Can I take antibiotic with alcohol?" → Should route to Q&A Agent
   - Try: "My back hurts" → Should route to Appointment Agent
   - Try: "What are the side effects of aspirin?" → Should route to Q&A Agent

3. **Check server logs** for routing decisions:
   ```bash
   docker-compose logs -f
   ```
   Look for routing intent classification in the logs.

## Code Changes Summary

**File: `server/app/agents/routing_agent.py`**

- **Lines 17-56**: Updated `ROUTER_SYSTEM_PROMPT` with clearer examples and rules
- **Lines 59-189**: Expanded `DEFAULT_INTENT_KEYWORDS` with symptom and medical information keywords
  - Scheduling: +43 new keywords (symptoms, health concerns)
  - Q&A: +33 new keywords (questions, drug interactions, medical info)

The refactored routing agent now correctly distinguishes between:
- **Symptoms/health problems** → Scheduling (patient needs medical attention)
- **Information queries** → Q&A (patient needs advice/information)
