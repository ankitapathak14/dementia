# NeuroAid

### AI-Based Cognitive Gaming and Memory Assistance Platform for Elderly Dementia Patients

NeuroAid is a cognitive-assistance platform designed for elderly users, with a focus on dementia patients in the North Eastern Region (NER) of India.

The platform combines simple cognitive activities, voice interaction, multilingual support, adaptive difficulty, daily-care assistance, offline functionality, and caregiver/doctor monitoring into one system.

The goal is not to diagnose dementia, but to provide an accessible platform for cognitive engagement, memory assistance, routine support, and caregiver-supported monitoring.

---

## Problem

Elderly people experiencing memory-related difficulties may face challenges with:

- Remembering everyday routines
- Following medication and hydration schedules
- Maintaining regular cognitive activity
- Using complex digital interfaces
- Communicating through text-heavy applications
- Accessing technology in areas with limited internet connectivity

Existing applications often focus on individual games or isolated reminders. NeuroAid brings these functions together and connects patient activity with caregiver monitoring.

---

## Our Solution

NeuroAid provides a simple and elderly-friendly environment where users can:

- Play cognitive activities
- Listen to instructions and stories using voice
- Use the application in multiple languages
- Practice memory and attention through different activities
- Receive daily-care reminders
- Continue relevant activities during poor connectivity
- Have their activity and progress monitored by authorized caregivers or doctors

The system follows a continuous interaction loop:

```text
Patient
   ↓
Cognitive Activity
   ↓
Performance Data
   ↓
Adaptive Difficulty
   ↓
Personalized Activity
   ↓
Caregiver / Doctor Monitoring
   ↓
Alerts and Review
```

---

## Key Features

### 🧠 Cognitive Games

NeuroAid includes multiple activities designed around different types of cognitive engagement:

- **Memory Match** – memory-based matching activity
- **Sequence Recall** – remembers and reproduces sequences
- **Object Recognition** – identifies familiar objects
- **Pattern Completion** – completes simple visual patterns
- **Daily Routine Recall** – recalls familiar daily activities
- **Rhythm Recall** – memory activity based on rhythm and sequence
- **Voice of the Village** – listens to simple culturally familiar stories and answers recall-based questions

The activities are designed to remain simple and accessible for elderly users.

---

### 🤖 Adaptive Difficulty

NeuroAid uses an adaptive difficulty mechanism based on the user's activity performance.

The system considers factors such as:

- Accuracy
- Error rate
- Response time
- Performance changes
- Fatigue-related indicators

Based on performance, the difficulty can move between different levels.

```text
User Performance
       ↓
Performance Analysis
       ↓
Difficulty Adjustment
       ↓
Next Activity
```

This allows the experience to be adjusted instead of giving every user exactly the same difficulty.

---

### 🗣️ Voice Interaction

Voice is an important part of NeuroAid's accessibility design.

The platform can provide:

- Spoken instructions
- Voice-based story narration
- Questions through voice
- Spoken feedback
- Page and interface announcements
- Voice-assisted interaction where supported

Visual controls are also maintained so that users are not dependent only on speech recognition.

---

### 🌐 Multilingual Support

NeuroAid is designed to support users who may be more comfortable using regional languages.

The current language architecture includes:

- English
- Hindi
- Bengali
- Assamese
- Meitei

The system is designed so that language support can be extended in the future.

---

### 🏡 Culturally Familiar Activities

The platform includes familiar everyday situations and themes instead of relying only on generic game content.

**Voice of the Village** is an example of this approach, using simple stories and recall questions based around familiar people, places, activities, and objects.

This helps make the interaction more understandable and relatable for the intended users.

---

### 💊 Daily Care and Memory Assistance

NeuroAid provides support for everyday routines through:

- Medication reminders
- Hydration reminders
- Daily activity reminders
- Medical appointment reminders
- Routine support
- Personal memory information

These features are intended as assistance tools and are not a replacement for professional medical care.

---

### 👨‍⚕️ Doctor and Caregiver Monitoring

Authorized caregivers or doctors can monitor relevant patient activity through the connected dashboard.

The monitoring system provides access to information such as:

- Patient activity
- Game performance
- Progress information
- Cognitive activity trends
- Reminders and routines
- Alerts requiring review
- Patient-specific details

The system connects patient-side activity with caregiver-side monitoring.

```text
Patient Activity
       ↓
Game Session / Result
       ↓
Backend
       ↓
Monitoring
       ↓
Caregiver / Doctor
       ↓
Review / Action
```

---

### 🚨 Caregiver Alerts

NeuroAid includes caregiver alerts based on observable activity patterns.

Alerts can be reviewed by authorized caregivers, allowing them to distinguish between new and already-reviewed activity flags.

The purpose of the alert system is to support timely review rather than automatically making a medical diagnosis.

---

### 📡 Offline Support

The platform is designed to support relevant activities during poor or unavailable internet connectivity.

Activity data can be stored locally and synchronized when connectivity becomes available.

```text
Activity
   ↓
Local Storage
   ↓
Internet Available?
   ├── No → Keep Data Locally
   └── Yes → Synchronize Data
```

This is particularly relevant for environments where reliable connectivity cannot always be assumed.

---

### 🔐 Security and Access Control

NeuroAid includes mechanisms for protecting patient-related information and controlling access.

The system includes:

- Role-based access control
- Patient-doctor assignment
- Consent handling
- Audit logging
- Restricted patient information access

Only authorized users should be able to access relevant patient information.

---

## System Architecture

```text
                         NEUROAID
                            │
             ┌──────────────┼──────────────┐
             │              │              │
             ▼              ▼              ▼
         PATIENT         VOICE &       ADAPTIVE
          PORTAL         LANGUAGE       ENGINE
             │              │              │
             └──────────────┼──────────────┘
                            ▼
                     COGNITIVE GAMES
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
          Memory        Voice of       Rhythm
           Games         Village        Recall
                            │
                            ▼
                    PERFORMANCE DATA
                            │
                            ▼
                    OFFLINE / SYNC
                            │
                            ▼
                   DOCTOR / CAREGIVER
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
         Progress         Alerts       Patient
                                         Details
```

---

## Technology Stack

### Frontend

- React
- JavaScript
- Vite
- React Router
- HTML
- CSS

### Backend

- Python
- FastAPI
- REST API architecture

### Storage and Offline Support

- Local data storage
- Browser-based storage
- IndexedDB
- Offline synchronization mechanism

### Voice and Accessibility

- Existing voice interaction architecture
- Speech and voice announcement utilities
- Multilingual localization system

---

## Project Structure

```text
NeuroAid
│
├── frontend
│   └── src
│       ├── components
│       ├── pages
│       ├── services
│       ├── context
│       ├── utils
│       └── data
│
├── backend
│   ├── routers
│   ├── services
│   ├── core
│   ├── data
│   └── tests
│
└── README.md
```

---

## Example User Flow

```text
User Login
    ↓
Select Language
    ↓
Patient Dashboard
    ↓
Choose Cognitive Activity
    ↓
Voice / Visual Instructions
    ↓
Complete Activity
    ↓
Performance Recorded
    ↓
Adaptive Difficulty
    ↓
Progress Updated
    ↓
Caregiver / Doctor Monitoring
    ↓
Alerts and Review
```

---

## Design Principles

NeuroAid is designed around the following principles:

- **Simple** – minimal and understandable interactions
- **Accessible** – voice and visual interaction
- **Personalized** – activity difficulty can adapt to performance
- **Multilingual** – supports multiple languages
- **Culturally Familiar** – uses relatable everyday contexts
- **Offline-Friendly** – supports limited-connectivity environments
- **Connected Care** – links patient activity with authorized caregivers
- **Privacy-Aware** – access control and consent mechanisms are included

---

## Scope

NeuroAid focuses on:

- Cognitive engagement
- Memory assistance
- Routine support
- Voice accessibility
- Multilingual interaction
- Caregiver-supported monitoring
- Offline-capable usage

NeuroAid is **not a diagnostic system** and does not replace professional medical assessment or treatment.

---

## Future Scope

Possible future improvements include:

- More regional languages
- More culturally personalized activities
- Personalized memory stories based on caregiver-provided information
- Improved speech recognition for regional languages
- More advanced personalization models
- Expanded analytics for caregivers
- Additional offline capabilities
- Integration with approved healthcare systems where appropriate

---

## Project Vision

NeuroAid aims to make cognitive-assistance technology more accessible to elderly users by combining simple activities, voice interaction, regional-language support, personalization, daily-care assistance, and caregiver connectivity in a single platform.

The core idea is to move beyond standalone cognitive games and create a connected system where:

```text
Engagement
    ↓
Performance
    ↓
Personalization
    ↓
Monitoring
    ↓
Caregiver Support
```

---

## Disclaimer

NeuroAid is an academic/project prototype intended for cognitive engagement, memory assistance, routine support, and caregiver-supported monitoring.

It is not intended to diagnose dementia, predict disease progression, or replace professional medical advice, diagnosis, or treatment.
