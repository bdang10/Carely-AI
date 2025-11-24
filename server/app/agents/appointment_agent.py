"""
AI Agent for handling appointment scheduling through natural conversation.
This agent queries the Provider database directly to find doctors and uses
OpenAI function calling for all appointment operations.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import or_
import json
import logging

from app.models.appointment import Appointment
from app.models.provider import Provider

# Configure logging
logger = logging.getLogger(__name__)


class AppointmentAgent:
    """AI Agent that handles appointment scheduling with direct database queries"""
    
    def __init__(self, openai_client: OpenAI):
        self.client = openai_client
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for the appointment agent"""
        return f"""You are an intelligent appointment management agent for Carely Healthcare.

Your responsibilities:
1. **Intelligently match symptoms to specialties** - Analyze user symptoms and automatically recommend the appropriate doctor specialty
2. **Search for doctors** - Use search_providers tool to find doctors by specialty or name
3. **Book appointments** - Schedule new appointments with doctors from the database
4. **List appointments** - Show user's upcoming and past appointments
5. **Update appointments** - Reschedule or modify existing appointments
6. **Cancel appointments** - Cancel appointments by ID

CRITICAL: INTELLIGENT SYMPTOM-TO-SPECIALTY MATCHING
You MUST automatically analyze user symptoms and recommend the appropriate specialty WITHOUT asking the user which type of doctor they need.

When a user describes symptoms or health concerns:
1. IMMEDIATELY identify the appropriate specialty using the SYMPTOM-TO-SPECIALTY MAPPING below
2. AUTOMATICALLY use search_providers with that specialty
3. Present the matching doctors with an explanation (e.g., "For your headache, I'd recommend seeing a primary care doctor. Here are some options...")
4. Do NOT ask "What type of doctor do you need?" - be proactive and intelligent

SYMPTOM-TO-SPECIALTY MAPPING (Use this to automatically recommend the right doctor):

**Primary Care / Family Medicine** (Start here for general symptoms):
- Headache, head pain, head hurts → PRIMARY CARE
- Fever, cold, flu, cough, sore throat, runny nose → PRIMARY CARE
- General pain, aches, "I don't feel well", feeling sick → PRIMARY CARE
- General check-ups, routine physicals, preventive care, annual exam → PRIMARY CARE
- Stomach ache, stomach pain, nausea, vomiting, diarrhea (non-emergency) → PRIMARY CARE
- Fatigue, tiredness, general weakness, feeling tired → PRIMARY CARE
- Minor injuries, cuts, bruises, scrapes → PRIMARY CARE
- Medication refills, prescription questions → PRIMARY CARE
- General health concerns, wellness visits → PRIMARY CARE
- "I need to see a doctor" (unspecified) → PRIMARY CARE

**Cardiology** (Heart and cardiovascular issues):
- Heart problems, heart pain, heart hurts, heart issue → CARDIOLOGY
- Chest pain (especially if cardiac-related), chest discomfort → CARDIOLOGY
- Heart palpitations, irregular heartbeat, arrhythmia → CARDIOLOGY
- High blood pressure, hypertension, BP issues → CARDIOLOGY
- Shortness of breath (if cardiac-related), difficulty breathing (cardiac) → CARDIOLOGY
- Heart disease, heart attack history, cardiac history → CARDIOLOGY
- "Heart problem", "heart condition", "cardiac issue" → CARDIOLOGY

**Orthopedics** (Bones, joints, muscles, musculoskeletal):
- Back pain, back hurts, lower back pain, upper back pain → ORTHOPEDICS
- Neck pain, neck hurts → ORTHOPEDICS
- Joint pain, joint problems, arthritis → ORTHOPEDICS
- Broken bones, fractures, sprains, strains → ORTHOPEDICS
- Sports injuries, muscle strains, muscle pain → ORTHOPEDICS
- Shoulder pain, knee pain, hip pain, ankle pain → ORTHOPEDICS
- Bone-related issues, bone pain → ORTHOPEDICS
- "My [body part] hurts" (musculoskeletal) → ORTHOPEDICS

**Neurology** (Brain and nervous system):
- Severe headaches, chronic headaches, migraines (if severe/chronic) → NEUROLOGY
- Seizures, epilepsy, convulsions → NEUROLOGY
- Dizziness, vertigo, balance problems → NEUROLOGY
- Numbness, tingling, pins and needles → NEUROLOGY
- Memory problems, cognitive issues, confusion → NEUROLOGY
- Stroke symptoms, neurological disorders → NEUROLOGY
- Tremors, movement disorders → NEUROLOGY

**Dermatology** (Skin, hair, nails):
- Skin rashes, rash, skin irritation → DERMATOLOGY
- Acne, pimples, skin breakouts → DERMATOLOGY
- Eczema, psoriasis, skin conditions → DERMATOLOGY
- Skin infections, skin growths, moles → DERMATOLOGY
- Hair loss, hair problems → DERMATOLOGY
- Nail problems, nail issues → DERMATOLOGY
- Allergic skin reactions, hives → DERMATOLOGY
- "Skin problem", "skin issue" → DERMATOLOGY

**Psychiatry** (Mental health):
- Depression, feeling depressed, sad, down → PSYCHIATRY
- Anxiety, anxious, panic attacks, stress → PSYCHIATRY
- Mental health concerns, mental health issues → PSYCHIATRY
- Mood disorders, bipolar, emotional problems → PSYCHIATRY
- "Mental health", "therapy", "counseling" → PSYCHIATRY

**Gynecology** (Women's health):
- Women's health issues, reproductive health → GYNECOLOGY
- Menstrual problems, period issues, pelvic pain → GYNECOLOGY
- Pregnancy-related concerns, prenatal care → GYNECOLOGY
- "Gynecologist", "women's health", "OB/GYN" → GYNECOLOGY

**Pediatrics** (Children):
- Any health concern for children/infants/babies → PEDIATRICS
- "My child", "my baby", "pediatric" → PEDIATRICS

**Emergency / Urgent Care**:
- Severe chest pain, severe difficulty breathing → EMERGENCY
- Severe injuries, trauma, major accidents → EMERGENCY
- Suspected stroke, heart attack symptoms → EMERGENCY
- Severe allergic reactions, anaphylaxis → EMERGENCY
- "Emergency", "urgent", "immediate", "right now" → EMERGENCY

SPECIALTY NAME MATCHING (When user specifies specialty directly):
- "cardiologist" or "cardiology" → search for "Cardiology"
- "primary care" or "family medicine" or "general practitioner" or "GP" → search for "Primary Care" or "Family Medicine"
- "surgeon" or "surgery" → search for "Surgery"
- "pediatrician" or "pediatrics" → search for "Pediatrics"
- "orthopedic" or "orthopedist" → search for "Orthopedics"
- "dermatologist" or "dermatology" → search for "Dermatology"
- "neurologist" or "neurology" → search for "Neurology"
- "psychiatrist" or "psychiatry" → search for "Psychiatry"
- "gynecologist" or "gynecology" or "OB/GYN" → search for "Gynecology"

WORKFLOW FOR BOOKING:
1. **Analyze user message**:
   - If symptoms described → AUTOMATICALLY identify specialty from SYMPTOM-TO-SPECIALTY MAPPING
   - If specialty specified → Use that specialty
   - If doctor name specified → Search by name
2. **IMMEDIATELY use search_providers** with the identified specialty (don't ask the user)
3. **Present doctors** with explanation: "For your [symptom], I'd recommend seeing a [specialty] doctor. Here are some options..."
4. Once user confirms doctor, date/time, and reason → use book_appointment tool

EXAMPLES OF INTELLIGENT MATCHING:
- User: "I have a headache" → AUTOMATICALLY search for "Primary Care" (don't ask what type of doctor)
- User: "I have heart problems" or "my heart hurts" → AUTOMATICALLY search for "Cardiology"
- User: "My back hurts" → AUTOMATICALLY search for "Orthopedics"
- User: "I need a check-up" → AUTOMATICALLY search for "Primary Care"
- User: "I have a skin rash" → AUTOMATICALLY search for "Dermatology"
- User: "I'm feeling anxious" → AUTOMATICALLY search for "Psychiatry"
- User: "I have chest pain" → AUTOMATICALLY search for "Cardiology" (unless clearly non-cardiac)
- User: "I have a fever and cough" → AUTOMATICALLY search for "Primary Care"

GUIDELINES:
- Always search for providers before booking - never assume a doctor exists
- If multiple doctors match, present all options to the user
- For booking: Ask for date/time, reason, and appointment type if not provided
- Handle date/time parsing intelligently (e.g., "tomorrow at 2pm", "next Monday morning")
- Default to 30-minute appointments unless specified
- Offer both in-person and virtual options
- For cancellations: Confirm before cancelling
- For updates: Ask what they want to change
- Users can reference appointments by their ID number (e.g., "appointment #5")

IMPORTANT:
- You MUST use the search_providers tool to find doctors before booking
- You MUST use the appropriate tool (book_appointment, update_appointment, cancel_appointment, list_appointments) for each operation
- Never create appointments without using the book_appointment tool
- Always verify provider exists in database before booking

Current date and time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    def _get_providers_by_specialty(self, specialty: str, db: Session) -> List[Provider]:
        """Query providers by specialty"""
        return db.query(Provider).filter(
            Provider.specialty.ilike(f"%{specialty}%"),
            Provider.is_active == True
        ).all()
    
    def _search_providers(self, query: str, db: Session) -> List[Provider]:
        """Search providers by name or specialty (fuzzy matching)"""
        return db.query(Provider).filter(
            or_(
                Provider.name.ilike(f"%{query}%"),
                Provider.specialty.ilike(f"%{query}%")
            ),
            Provider.is_active == True
        ).all()
    
    def _search_providers_tool(self, query: str, db: Session) -> Tuple[str, Dict]:
        """Tool handler for searching providers"""
        try:
            providers = self._search_providers(query, db)
            
            if not providers:
                return f"I couldn't find any doctors matching '{query}'. Please try a different search term or specialty.", {
                    "action": "search_providers",
                    "query": query,
                    "providers": [],
                    "count": 0
                }
            
            provider_list = []
            response = f"🔍 **Found {len(providers)} doctor(s) matching '{query}':**\n\n"
            
            for provider in providers:
                response += f"**{provider.name}**\n"
                if provider.specialty:
                    response += f"   • Specialty: {provider.specialty}\n"
                if provider.email:
                    response += f"   • Email: {provider.email}\n"
                if provider.phone_number:
                    response += f"   • Phone: {provider.phone_number}\n"
                response += f"   • ID: {provider.id}\n\n"
                
                provider_list.append({
                    "id": provider.id,
                    "name": provider.name,
                    "specialty": provider.specialty,
                    "email": provider.email,
                    "phone_number": provider.phone_number
                })
            
            response += "\n💡 To book an appointment, tell me which doctor you'd like to see and when."
            
            return response, {
                "action": "search_providers",
                "query": query,
                "providers": provider_list,
                "count": len(providers)
            }
        except Exception as e:
            return f"I encountered an error searching for doctors: {str(e)}", {
                "action": "search_providers",
                "error": str(e),
                "success": False
            }
    
    def _book_appointment_tool(
        self,
        patient_id: int,
        provider_id: int,
        scheduled_time: str,
        reason: str,
        appointment_type: str = "consultation",
        is_virtual: bool = False,
        duration_minutes: int = 30,
        db: Session = None
    ) -> Tuple[str, Dict]:
        """Tool handler for booking appointments"""
        try:
            # Verify provider exists
            provider = db.query(Provider).filter(
                Provider.id == provider_id,
                Provider.is_active == True
            ).first()
            
            if not provider:
                return f"Provider with ID {provider_id} not found or is inactive. Please search for providers first.", {
                    "action": "book_appointment",
                    "success": False,
                    "error": "Provider not found"
                }
            
            # Parse scheduled time
            try:
                scheduled_datetime = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
                # Remove timezone info for database storage
                if scheduled_datetime.tzinfo:
                    scheduled_datetime = scheduled_datetime.replace(tzinfo=None)
            except ValueError:
                return f"Invalid date/time format: {scheduled_time}. Please use ISO format (e.g., '2024-11-22T10:00:00').", {
                    "action": "book_appointment",
                    "success": False,
                    "error": "Invalid date/time format"
                }
            
            # Check if time is in the past
            if scheduled_datetime < datetime.now():
                return "Cannot book appointments in the past. Please choose a future date and time.", {
                    "action": "book_appointment",
                    "success": False,
                    "error": "Past date/time"
                }
            
            # Create appointment
            appointment = Appointment(
                patient_id=patient_id,
                doctor_name=provider.name,
                appointment_type=appointment_type,
                scheduled_time=scheduled_datetime,
                duration_minutes=duration_minutes,
                reason=reason,
                is_virtual=is_virtual,
                status='scheduled',
                location='Virtual' if is_virtual else 'Main Clinic'
            )
            
            db.add(appointment)
            db.commit()
            db.refresh(appointment)
            
            response = f"""✅ **Appointment Booked Successfully!**

📅 **Appointment Details:**
- **ID:** #{appointment.id}
- **Doctor:** {appointment.doctor_name}
- **Type:** {appointment.appointment_type.title()}
- **Date & Time:** {appointment.scheduled_time.strftime('%A, %B %d, %Y at %I:%M %p')}
- **Duration:** {appointment.duration_minutes} minutes
- **Location:** {'Virtual Meeting' if appointment.is_virtual else 'Main Clinic'}
- **Reason:** {appointment.reason}

You'll receive a reminder 24 hours before your appointment. If you need to reschedule or cancel, just let me know!"""
            
            return response, {
                "action": "book_appointment",
                "success": True,
                "appointment_id": appointment.id,
                "appointment": {
                    "id": appointment.id,
                    "doctor_name": appointment.doctor_name,
                    "appointment_type": appointment.appointment_type,
                    "scheduled_time": appointment.scheduled_time.isoformat(),
                    "duration_minutes": appointment.duration_minutes,
                    "is_virtual": bool(appointment.is_virtual),
                    "status": appointment.status,
                    "reason": appointment.reason
                }
            }
        except Exception as e:
            db.rollback()
            return f"I encountered an error booking the appointment: {str(e)}", {
                "action": "book_appointment",
                "success": False,
                "error": str(e)
            }
    
    def _list_appointments_tool(
        self,
        patient_id: int,
        db: Session,
        limit: int = 10,
        status_filter: Optional[str] = None
    ) -> Tuple[str, Dict]:
        """Tool handler for listing appointments"""
        try:
            query = db.query(Appointment).filter(
                Appointment.patient_id == patient_id
            )
            
            if status_filter:
                query = query.filter(Appointment.status == status_filter)
            else:
                # Exclude cancelled by default unless specifically requested
                query = query.filter(Appointment.status != 'cancelled')
            
            appointments = query.order_by(Appointment.scheduled_time.desc()).limit(limit).all()
            
            if not appointments:
                return "You don't have any appointments scheduled yet. Would you like to book one?", {
                    "action": "list_appointments",
                    "appointments": [],
                    "count": 0
                }
            
            response = f"📅 **Your Appointments** ({len(appointments)} total):\n\n"
            
            appointment_list = []
            for apt in appointments:
                status_emoji = {
                    'scheduled': '🟢',
                    'confirmed': '✅',
                    'completed': '✔️',
                    'cancelled': '❌'
                }.get(apt.status, '⚪')
                
                response += f"{status_emoji} **Appointment #{apt.id}**\n"
                response += f"   • Doctor: {apt.doctor_name}\n"
                response += f"   • Type: {apt.appointment_type.title()}\n"
                response += f"   • Date: {apt.scheduled_time.strftime('%A, %B %d, %Y at %I:%M %p')}\n"
                response += f"   • Status: {apt.status.title()}\n"
                if apt.reason:
                    response += f"   • Reason: {apt.reason}\n"
                response += f"   • Location: {'Virtual' if apt.is_virtual else (apt.location or 'Main Clinic')}\n"
                response += "\n"
                
                appointment_list.append({
                    "id": apt.id,
                    "doctor_name": apt.doctor_name,
                    "appointment_type": apt.appointment_type,
                    "scheduled_time": apt.scheduled_time.isoformat(),
                    "status": apt.status,
                    "reason": apt.reason,
                    "is_virtual": bool(apt.is_virtual),
                    "duration_minutes": apt.duration_minutes
                })
            
            response += "\n💡 You can cancel or reschedule any appointment by telling me the appointment number."
            
            return response, {
                "action": "list_appointments",
                "appointments": appointment_list,
                "count": len(appointments)
            }
        except Exception as e:
            return f"I encountered an error retrieving your appointments: {str(e)}", {
                "action": "list_appointments",
                "error": str(e),
                "success": False
            }
    
    def _cancel_appointment_tool(
        self,
        patient_id: int,
        appointment_id: int,
        db: Session
    ) -> Tuple[str, Dict]:
        """Tool handler for canceling appointments"""
        try:
            appointment = db.query(Appointment).filter(
                Appointment.id == appointment_id,
                Appointment.patient_id == patient_id
            ).first()
            
            if not appointment:
                return f"I couldn't find appointment #{appointment_id} for your account. Please check the appointment number.", {
                    "action": "cancel_appointment",
                    "success": False,
                    "error": "Appointment not found"
                }
            
            if appointment.status == 'cancelled':
                return f"Appointment #{appointment_id} is already cancelled.", {
                    "action": "cancel_appointment",
                    "success": False,
                    "error": "Already cancelled"
                }
            
            old_status = appointment.status
            appointment.status = 'cancelled'
            appointment.updated_at = datetime.utcnow()
            db.commit()
            
            response = f"""❌ **Appointment Cancelled**

Appointment #{appointment.id} has been successfully cancelled.

**Cancelled Appointment Details:**
• Doctor: {appointment.doctor_name}
• Type: {appointment.appointment_type.title()}
• Was scheduled for: {appointment.scheduled_time.strftime('%A, %B %d, %Y at %I:%M %p')}
• Previous status: {old_status.title()}

If you'd like to book a new appointment, just let me know!"""
            
            return response, {
                "action": "cancel_appointment",
                "success": True,
                "appointment_id": appointment.id,
                "cancelled_appointment": {
                    "id": appointment.id,
                    "doctor_name": appointment.doctor_name,
                    "scheduled_time": appointment.scheduled_time.isoformat(),
                    "status": appointment.status
                }
            }
        except Exception as e:
            db.rollback()
            return f"I encountered an error cancelling the appointment: {str(e)}", {
                "action": "cancel_appointment",
                "success": False,
                "error": str(e)
            }
    
    def _update_appointment_tool(
        self,
        patient_id: int,
        appointment_id: int,
        updates: Dict,
        db: Session
    ) -> Tuple[str, Dict]:
        """Tool handler for updating appointments"""
        try:
            appointment = db.query(Appointment).filter(
                Appointment.id == appointment_id,
                Appointment.patient_id == patient_id
            ).first()
            
            if not appointment:
                return f"I couldn't find appointment #{appointment_id} for your account.", {
                    "action": "update_appointment",
                    "success": False,
                    "error": "Appointment not found"
                }
            
            if appointment.status == 'cancelled':
                return f"Appointment #{appointment_id} is cancelled. Would you like to book a new one instead?", {
                    "action": "update_appointment",
                    "success": False,
                    "error": "Appointment is cancelled"
                }
            
            old_time = appointment.scheduled_time
            
            # Update fields
            if 'scheduled_time' in updates:
                try:
                    new_time = datetime.fromisoformat(str(updates['scheduled_time']).replace('Z', '+00:00'))
                    if new_time.tzinfo:
                        new_time = new_time.replace(tzinfo=None)
                    if new_time < datetime.now():
                        return "Cannot reschedule to a past date/time. Please choose a future date and time.", {
                            "action": "update_appointment",
                            "success": False,
                            "error": "Past date/time"
                        }
                    appointment.scheduled_time = new_time
                except (ValueError, TypeError) as e:
                    return f"Invalid date/time format: {updates.get('scheduled_time')}. Please use ISO format.", {
                        "action": "update_appointment",
                        "success": False,
                        "error": "Invalid date/time format"
                    }
            
            if 'reason' in updates:
                appointment.reason = str(updates['reason'])
            if 'notes' in updates:
                appointment.notes = str(updates['notes'])
            if 'duration_minutes' in updates:
                appointment.duration_minutes = int(updates['duration_minutes'])
            if 'is_virtual' in updates:
                appointment.is_virtual = bool(updates['is_virtual'])
                appointment.location = 'Virtual' if updates['is_virtual'] else 'Main Clinic'
            
            appointment.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(appointment)
            
            response = f"""✅ **Appointment Updated**

Appointment #{appointment.id} has been successfully updated.

**Updated Details:**
• Doctor: {appointment.doctor_name}
• Type: {appointment.appointment_type.title()}
• New Date & Time: {appointment.scheduled_time.strftime('%A, %B %d, %Y at %I:%M %p')}
• Duration: {appointment.duration_minutes} minutes
• Location: {'Virtual' if appointment.is_virtual else appointment.location}
• Status: {appointment.status.title()}

"""
            if old_time != appointment.scheduled_time:
                response += f"📅 Changed from: {old_time.strftime('%A, %B %d, %Y at %I:%M %p')}\n"
            
            response += "\nYou'll receive a reminder 24 hours before your appointment."
            
            return response, {
                "action": "update_appointment",
                "success": True,
                "appointment_id": appointment.id,
                "updated_appointment": {
                    "id": appointment.id,
                    "doctor_name": appointment.doctor_name,
                    "scheduled_time": appointment.scheduled_time.isoformat(),
                    "duration_minutes": appointment.duration_minutes,
                    "is_virtual": bool(appointment.is_virtual),
                    "status": appointment.status
                }
            }
        except Exception as e:
            db.rollback()
            return f"I encountered an error updating the appointment: {str(e)}", {
                "action": "update_appointment",
                "success": False,
                "error": str(e)
            }
    
    def _get_tools(self) -> List[Dict]:
        """Define all function tools for OpenAI"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_providers",
                    "description": "Search for doctors/providers by specialty or name. Use this BEFORE booking to find available doctors.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search term - can be a specialty (e.g., 'cardiology', 'primary care') or doctor name (e.g., 'Dr. Smith')"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "book_appointment",
                    "description": "Book a new medical appointment. Requires provider_id from search_providers, scheduled_time, and reason.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "provider_id": {
                                "type": "integer",
                                "description": "ID of the provider/doctor from search_providers results"
                            },
                            "scheduled_time": {
                                "type": "string",
                                "description": "Appointment date and time in ISO format (e.g., '2024-11-22T10:00:00')"
                            },
                            "reason": {
                                "type": "string",
                                "description": "Reason for the appointment"
                            },
                            "appointment_type": {
                                "type": "string",
                                "enum": ["consultation", "follow-up", "emergency", "check-up"],
                                "description": "Type of appointment (default: consultation)"
                            },
                            "is_virtual": {
                                "type": "boolean",
                                "description": "Whether this is a virtual appointment (default: false)"
                            },
                            "duration_minutes": {
                                "type": "integer",
                                "description": "Duration in minutes (default: 30)"
                            }
                        },
                        "required": ["provider_id", "scheduled_time", "reason"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_appointments",
                    "description": "List user's appointments. Can filter by status if needed.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "status_filter": {
                                "type": "string",
                                "enum": ["scheduled", "confirmed", "completed", "cancelled"],
                                "description": "Optional: Filter by status. If not provided, shows all non-cancelled appointments."
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of appointments to return (default: 10)"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_appointment",
                    "description": "Update/reschedule an existing appointment. Can change date/time, reason, notes, duration, or virtual status.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "appointment_id": {
                                "type": "integer",
                                "description": "ID of the appointment to update"
                            },
                            "scheduled_time": {
                                "type": "string",
                                "description": "New date and time in ISO format (e.g., '2024-11-22T15:00:00')"
                            },
                            "reason": {
                                "type": "string",
                                "description": "Updated reason for the appointment"
                            },
                            "notes": {
                                "type": "string",
                                "description": "Additional notes"
                            },
                            "duration_minutes": {
                                "type": "integer",
                                "description": "Updated duration in minutes"
                            },
                            "is_virtual": {
                                "type": "boolean",
                                "description": "Whether this is a virtual appointment"
                            }
                        },
                        "required": ["appointment_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "cancel_appointment",
                    "description": "Cancel an existing appointment by ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "appointment_id": {
                                "type": "integer",
                                "description": "ID of the appointment to cancel"
                            }
                        },
                        "required": ["appointment_id"]
                    }
                }
            }
        ]
    
    async def process_appointment_request(
        self,
        message: str,
        conversation_history: List[Dict],
        patient_id: int,
        db: Session,
        intent: str = None
    ) -> Tuple[str, Optional[Dict]]:
        """
        Process an appointment-related message using tool calling.
        Returns (AI response, appointment_data)
        """
        # Build messages for OpenAI
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # Add conversation history
        messages.extend(conversation_history)
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        try:
            # Get tools
            tools = self._get_tools()
            
            # Call OpenAI API with function calling
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=1000
            )
            
            message_obj = response.choices[0].message
            ai_response = message_obj.content.strip() if message_obj.content else ""
            appointment_data = None
            
            # Process tool calls
            if message_obj.tool_calls:
                # Add assistant message with tool calls to conversation
                messages.append({
                    "role": "assistant",
                    "content": message_obj.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message_obj.tool_calls
                    ]
                })
                
                # Handle multiple tool calls (though typically one at a time)
                first_tool_response = None
                for tool_call in message_obj.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"🔧 Tool called: {function_name}")
                    logger.debug(f"   Args: {function_args}")
                    
                    # Execute the appropriate tool
                    if function_name == "search_providers":
                        tool_response, tool_data = self._search_providers_tool(
                            query=function_args.get("query", ""),
                            db=db
                        )
                        appointment_data = tool_data
                    
                    elif function_name == "book_appointment":
                        tool_response, tool_data = self._book_appointment_tool(
                            patient_id=patient_id,
                            provider_id=function_args.get("provider_id"),
                            scheduled_time=function_args.get("scheduled_time"),
                            reason=function_args.get("reason"),
                            appointment_type=function_args.get("appointment_type", "consultation"),
                            is_virtual=function_args.get("is_virtual", False),
                            duration_minutes=function_args.get("duration_minutes", 30),
                            db=db
                        )
                        appointment_data = tool_data
                    
                    elif function_name == "list_appointments":
                        tool_response, tool_data = self._list_appointments_tool(
                            patient_id=patient_id,
                            db=db,
                            limit=function_args.get("limit", 10),
                            status_filter=function_args.get("status_filter")
                        )
                        appointment_data = tool_data
                    
                    elif function_name == "update_appointment":
                        updates = {k: v for k, v in function_args.items() if k != "appointment_id"}
                        tool_response, tool_data = self._update_appointment_tool(
                            patient_id=patient_id,
                            appointment_id=function_args.get("appointment_id"),
                            updates=updates,
                            db=db
                        )
                        appointment_data = tool_data
                    
                    elif function_name == "cancel_appointment":
                        tool_response, tool_data = self._cancel_appointment_tool(
                            patient_id=patient_id,
                            appointment_id=function_args.get("appointment_id"),
                            db=db
                        )
                        appointment_data = tool_data
                    
                    # Store first tool response for fallback
                    if first_tool_response is None:
                        first_tool_response = tool_response
                    
                    # Add tool response to messages for follow-up
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_response
                    })
                
                # Make a follow-up call to get final natural language response
                follow_up_response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=0.3,
                    max_tokens=500
                )
                follow_up_message = follow_up_response.choices[0].message
                
                # Use LLM response if available, otherwise use tool response
                if follow_up_message.content:
                    ai_response = follow_up_message.content.strip()
                elif first_tool_response:
                    # Fallback to first tool response if LLM didn't generate content
                    ai_response = first_tool_response
            
            # If no tool was called and no response, generate a helpful response
            if not ai_response:
                ai_response = "I'm here to help you with appointments. You can search for doctors, book appointments, view your appointments, or cancel/reschedule existing ones. What would you like to do?"
            
            return ai_response, appointment_data
            
        except Exception as e:
            error_message = f"I apologize, but I encountered an error while processing your appointment request: {str(e)}"
            import traceback
            traceback.print_exc()
            return error_message, {"error": str(e), "success": False}
    
    def format_appointment_confirmation(self, appointment: Appointment) -> str:
        """Format appointment confirmation message"""
        return f"""✅ **Appointment Confirmed!**

📋 **Details:**
- **ID:** #{appointment.id}
- **Doctor:** {appointment.doctor_name}
- **Type:** {appointment.appointment_type.title()}
- **Date & Time:** {appointment.scheduled_time.strftime('%A, %B %d, %Y at %I:%M %p')}
- **Duration:** {appointment.duration_minutes} minutes
- **Location:** {'Virtual Meeting' if appointment.is_virtual else appointment.location}
- **Status:** {appointment.status.title()}

📝 **Reason:** {appointment.reason}

We'll send you a reminder 24 hours before your appointment. See you then!"""
