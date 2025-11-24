"""
Intent routing agent that mirrors the experimental notebook logic.
It combines lightweight keyword stemming heuristics with an optional LLM
verification step to decide whether a message belongs to scheduling or Q&A.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from nltk.stem import PorterStemmer
from openai import OpenAI


ROUTER_SYSTEM_PROMPT = """You are an intent router for healthcare queries.
Classify the user's message into EXACTLY ONE of:
- Scheduling
- Q&A
(Use "User_Decision" if it is perfectly balanced and cannot be decided, or if neither fits clearly.)

Return ONLY a strict JSON object. All keys must be lowercase.
No extra text before or after the JSON.

Schema (exact keys and types):
{
  "schema_version": "1.0",            // string
  "intent": "scheduling|qna|user_decision",  // string, one of these, lowercase
  "confidence": 0.0,                  // number in [0,1]
  "rationale": "short reason",        // string, ≤ 20 words
  "counts": {"scheduling": 0, "qna": 0},  // object with two integers (0 or positive)
  "evidence": [],                     // list of short strings, each ≤ 3 words
  "source": "llm",                    // string: always "llm" here
  "raw_text": "..."                   // echo user message
}

Rules:
- Be deterministic and concise. Temperature is 0.
- SCHEDULING intent (patient needs to see a doctor):
  * Explicitly requests to book/change/cancel an appointment
  * Reports symptoms or health problems (headache, pain, fever, illness, injury)
  * Expresses health concerns requiring medical attention ("I have...", "I feel...", "experiencing...")
  * Examples: "I have a headache", "My back hurts", "I'm feeling sick", "I need to see a doctor"

- Q&A intent (seeking information, no appointment needed):
  * Asks for general medical information or advice
  * Questions about medications, drug interactions, dosages
  * Policy/insurance/billing questions
  * Operating hours, location, general facility information
  * Examples: "Can I take antibiotic with alcohol?", "What are the side effects of aspirin?", "What are your hours?"

- If votes tie or unclear: intent = "user_decision".

Key distinction: Symptoms/health problems → scheduling | Information/advice questions → q&a
"""


DEFAULT_INTENT_KEYWORDS: Dict[str, List[str]] = {
    "Scheduling": [
        # Appointment-related keywords
        "schedule",
        "appointment",
        "book",
        "doctor",
        "meeting",
        "make",
        "time",
        "cancel",
        "update",
        "reschedule",
        "date",
        "available",
        "availability",
        "department",
        "visit",
        "slot",
        "slots",
        "openings",
        "see",
        "see a doctor",
        "follow-up",
        "check-in",
        "consultation",
        "consult",
        # Symptom keywords that indicate need to see a doctor
        "headache",
        "pain",
        "hurt",
        "hurting",
        "ache",
        "aching",
        "fever",
        "sick",
        "ill",
        "dizzy",
        "nausea",
        "vomiting",
        "cough",
        "cold",
        "flu",
        "sore throat",
        "swelling",
        "rash",
        "bleeding",
        "injury",
        "injured",
        "broken",
        "sprain",
        "chest pain",
        "shortness of breath",
        "breathing problem",
        "stomach ache",
        "back pain",
        "migraine",
        "fatigue",
        "tired",
        "weakness",
        "infection",
        "allergic",
        "allergy",
        "emergency",
        "urgent",
        # Health concerns requiring medical attention
        "i have",
        "i feel",
        "feeling",
        "experiencing",
        "suffering",
    ],
    "Q&A": [
        # General information queries
        "question",
        "query",
        "general",
        "answer",
        "ask",
        "hours",
        "operating hours",
        "open",
        "close",
        # Question words for informational queries
        "how",
        "what",
        "which",
        "when",
        "why",
        "where",
        "should i",
        "can i",
        "is it safe",
        "is it okay",
        # Medication and treatment information
        "side effect",
        "side effects",
        "dosage",
        "dose",
        "instruction",
        "directions",
        "medication",
        "medicine",
        "drug",
        "prescription",
        "over-the-counter",
        "otc",
        "antibiotic",
        "antibiotics",
        "painkiller",
        "vitamin",
        "supplement",
        # Drug interactions and safety
        "interaction",
        "interact",
        "mix",
        "combine",
        "together",
        "with alcohol",
        "alcohol",
        "drinking",
        # Administrative and policy queries
        "policy",
        "coverage",
        "benefit",
        "insurance",
        "copay",
        "cost",
        "price",
        "payment",
        "refill",
        "faq",
        # General medical information
        "advice",
        "recommend",
        "recommendation",
        "information",
        "info",
        "tell me about",
        "explain",
        "normal",
        "common",
    ],
}


@dataclass
class RoutingResult:
    intent: str
    confidence: float
    rationale: str
    counts: Dict[str, int]
    evidence: List[Dict[str, Any]]
    source: str
    raw_text: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "1.0",
            "intent": self.intent,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "counts": self.counts,
            "evidence": self.evidence,
            "source": self.source,
            "raw_text": self.raw_text,
        }


class RoutingAgent:
    """
    Hybrid keyword + LLM routing agent for scheduling vs Q&A intents.
    Also coordinates information flow between agents.
    """

    def __init__(
        self,
        openai_client: Optional[OpenAI],
        *,
        intent_map: Optional[Dict[str, List[str]]] = None,
        system_prompt: str = ROUTER_SYSTEM_PROMPT,
        router_model: str = "gpt-4o-mini",
        min_confidence_for_rules: float = 0.6,
    ) -> None:
        self.client = openai_client
        self.intent_map = intent_map or DEFAULT_INTENT_KEYWORDS
        self.system_prompt = system_prompt
        self.router_model = router_model
        self.min_confidence_for_rules = min_confidence_for_rules

        self.stemmer = PorterStemmer()
        self.sch_stems = {self.stemmer.stem(w) for w in self.intent_map["Scheduling"]}
        self.qna_stems = {self.stemmer.stem(w) for w in self.intent_map["Q&A"]}

    # --- Keyword / stemming pipeline ---
    def _tokenize(self, text: str) -> List[str]:
        tokens = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?|[0-9]+", text or "")
        return [t.lower() for t in tokens]

    def _scan_token(self, token: str) -> Optional[str]:
        stem = self.stemmer.stem(token)
        if stem in self.sch_stems or token in self.intent_map["Scheduling"]:
            return "scheduling"
        if stem in self.qna_stems or token in self.intent_map["Q&A"]:
            return "qna"
        return None

    def _rule_scan(self, text: str) -> RoutingResult:
        tokens = self._tokenize(text)
        evidence: List[Dict[str, Any]] = []

        for index, token in enumerate(tokens):
            task = self._scan_token(token)
            if task:
                evidence.append(
                    {"index": index, "keyword": token, "specific_task": task.title(), "match": True}
                )

        scheduling_hits = sum(1 for e in evidence if e["specific_task"] == "Scheduling")
        qna_hits = sum(1 for e in evidence if e["specific_task"] == "Q&A")

        total = max(1, scheduling_hits + qna_hits)
        distance = abs(scheduling_hits - qna_hits)
        confidence = 0.5 + 0.5 * (distance / total)

        if scheduling_hits > qna_hits:
            intent = "scheduling"
            rationale = "keyword votes favor scheduling"
        elif scheduling_hits < qna_hits:
            intent = "qna"
            rationale = "keyword votes favor qna"
        else:
            intent = "user_decision"
            rationale = "keyword votes equal or unclear"

        counts = {"scheduling": scheduling_hits, "qna": qna_hits}

        return RoutingResult(
            intent=intent,
            confidence=confidence,
            rationale=rationale,
            counts=counts,
            evidence=evidence,
            source="stemming rule",
            raw_text=text,
        )

    # --- LLM fallback ---
    def _llm_classification(self, text: str) -> RoutingResult:
        if not self.client:
            return RoutingResult(
                intent="user_decision",
                confidence=0.5,
                rationale="llm unavailable",
                counts={"scheduling": 0, "qna": 0},
                evidence=[],
                source="fallback",
                raw_text=text,
            )

        messages: List[Dict[str, str]] = [{"role": "system", "content": self.system_prompt}]
        messages.append({"role": "user", "content": f"message: {text}"})

        try:
            response = self.client.chat.completions.create(
                model=self.router_model,
                messages=messages,
                temperature=0,
                max_tokens=300,
            )
            content = response.choices[0].message.content.strip()
            data = json.loads(content)
        except Exception:
            data = {
                "schema_version": "1.0",
                "intent": "user_decision",
                "confidence": 0.5,
                "rationale": "invalid llm json",
                "counts": {"scheduling": 0, "qna": 0},
                "evidence": [],
                "source": "llm",
                "raw_text": text,
            }

        # Normalize intent: convert "q&a" to "qna" for consistency
        intent = str(data.get("intent", "user_decision")).lower()
        if intent == "q&a":
            intent = "qna"
        intent = intent.replace("&", "")  # Remove any remaining & characters

        return RoutingResult(
            intent=intent,
            confidence=float(data.get("confidence", 0.5)),
            rationale=str(data.get("rationale", "")),
            counts=data.get("counts", {"scheduling": 0, "qna": 0}) or {"scheduling": 0, "qna": 0},
            evidence=data.get("evidence", []) or [],
            source="llm",
            raw_text=text,
        )

    def hybrid_decision(self, text: str) -> RoutingResult:
        if not text:
            return RoutingResult(
                intent="user_decision",
                confidence=0.5,
                rationale="empty or missing text",
                counts={"scheduling": 0, "qna": 0},
                evidence=[],
                source="guard",
                raw_text="",
            )

        rule_result = self._rule_scan(text)

        if rule_result.confidence < self.min_confidence_for_rules:
            llm_result = self._llm_classification(text)

            # If LLM did not return schema, fall back to rule result
            if not llm_result.intent:
                return rule_result
            return llm_result

        return rule_result

    def route_decision(self, text: str) -> Dict[str, Any]:
        result = self.hybrid_decision(text)
        intent = result.intent or "user_decision"
        confidence = result.confidence or 0.5

        if confidence >= 0.6 and intent == "scheduling":
            next_service = "appointment_service"
            action = "book_appointment"
        elif confidence >= 0.6 and intent == "qna":
            next_service = "qna_service"
            action = "answer_question"
        else:
            next_service = "frontend"
            action = "ask_user_decision"

        payload = {
            "text": text,
            "language": "English",
        }

        return {
            "intent": intent,
            "confidence": confidence,
            "next_service": next_service,
            "action": action,
            "payload": payload,
            "raw_result": result.to_dict(),
        }

    def get_appointment_context(self) -> Dict[str, str]:
        """
        Get doctor and schedule information from QnA agent for appointment scheduling.
        This method coordinates information retrieval for the appointment agent.
        """
        if not self.qna_agent:
            print("⚠️  Routing Agent: No QnA Agent available")
            return {
                "doctor_info": "Doctor information available upon request.",
                "schedule_info": "Schedule information available upon request."
            }
        
        try:
            # Query QnA agent for doctor information
            # Use multiple targeted queries to get comprehensive coverage
            print("🔄 Routing Agent: Requesting doctor information from QnA Agent...")
            print(f"   QnA Agent has RAG: {hasattr(self.qna_agent, 'rag_instance') and self.qna_agent.rag_instance is not None}")
            print(f"   QnA Agent use_rag: {getattr(self.qna_agent, 'use_rag', False)}")
            
            # Query for different specialties to get better RAG coverage
            # Each query retrieves top_k=3 chunks, so multiple queries = more coverage
            queries = [
                "cardiology doctors cardiologists heart specialists available appointment",
                "primary care family medicine internal medicine doctors available",
                "surgery orthopedic pediatric specialists gynecology doctors",
                "find provider doctor names specialties schedule appointment booking"
            ]
            
            all_doctor_info = []
            for query in queries:
                print(f"   Querying: {query[:50]}...")
                response = self.qna_agent.generate_response(query)
                if response and len(response) > 100:  # Only include substantial responses
                    all_doctor_info.append(response)
            
            # Combine all responses
            doctor_info = "\n\n".join(all_doctor_info)
            
            print("✅ Routing Agent: Received doctor information from QnA Agent")
            print(f"   Total info length: {len(doctor_info)} characters")
            print(f"   Doctor info preview: {doctor_info[:300]}...")
            
            return {
                "doctor_info": doctor_info,
                "schedule_info": "Available through doctor information above"
            }
        except Exception as e:
            print(f"⚠️  Routing Agent: Error getting context from QnA agent: {e}")
            import traceback
            traceback.print_exc()
            return {
                "doctor_info": "Doctor information temporarily unavailable.",
                "schedule_info": "Schedule information temporarily unavailable."
            }
    
    def get_doctor_schedule(self, doctor_name: str) -> str:
        """
        Get specific doctor's schedule from QnA agent.
        This method coordinates schedule retrieval for the appointment agent.
        """
        if not self.qna_agent:
            return "Schedule information available upon request."
        
        try:
            print(f"🔄 Routing Agent: Requesting schedule for {doctor_name} from QnA Agent...")
            schedule_info = self.qna_agent.generate_response(
                f"What is {doctor_name}'s schedule and availability?"
            )
            print(f"✅ Routing Agent: Received schedule for {doctor_name}")
            return schedule_info
        except Exception as e:
            print(f"⚠️  Routing Agent: Error getting schedule from QnA agent: {e}")
            return f"Schedule for {doctor_name} temporarily unavailable."


