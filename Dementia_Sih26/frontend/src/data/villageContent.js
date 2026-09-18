/**
 * villageContent.js — Multilingual Culturally Grounded Village Stories
 * ====================================================================
 * Gentle, everyday community stories inspired by village and household life
 * in the North Eastern Region of India. Designed specifically for elderly
 * dementia-friendly cognitive recall exercises.
 *
 * Fully localized across 5 supported languages:
 * - English (en-IN)
 * - Assamese (as-IN)
 * - Hindi (hi-IN)
 * - Bengali (bn-IN)
 * - Meitei (mni-IN)
 *
 * Difficulty Levels:
 * - Level 1: Direct Recall (1–2 sentences, 2 large choices)
 * - Level 2: Object & Event Recall (2 sentences, 3 choices)
 * - Level 3: Context & Detail Recall (2–3 sentences, 3–4 choices)
 */

export const VILLAGE_STORIES = [
  // ───────────────────────────────────────────────────────────────────────────
  // LEVEL 1: DIRECT RECALL (2 Choices)
  // ───────────────────────────────────────────────────────────────────────────
  {
    id: "vlg-101",
    level: 1,
    icon: "🍌",
    domain: "Direct Recall",
    story: {
      "en-IN": "Mother went to the village market. She bought fresh bananas.",
      "as-IN": "মা গাঁৱৰ বজাৰলৈ গৈছিল। তেওঁ পকা কল কিনি আনিছিল।",
      "hi-IN": "माँ गाँव के बाज़ार गई थीं। उन्होंने ताज़ा केले खरीदे।",
      "bn-IN": "মা গ্রামের বাজারে গিয়েছিলেন। তিনি টাটকা কলা কিনেছিলেন।",
      "mni-IN": "ইমা খুঙ্গংগী কৈথেলদা চৎখি। মহাক্না হৌজিবা লফোই লৈখি।",
    },
    question: {
      "en-IN": "What did Mother buy at the market?",
      "as-IN": "মায়ে বজাৰৰ পৰা কি কিনি আনিছিল?",
      "hi-IN": "माँ ने बाज़ार से क्या खरीदा?",
      "bn-IN": "মা বাজার থেকে কী কিনেছিলেন?",
      "mni-IN": "ইমানা কৈথেলদগী করি লৈখিবগে?",
    },
    options: [
      {
        id: "opt-1",
        text: {
          "en-IN": "Bananas",
          "as-IN": "কল",
          "hi-IN": "केले",
          "bn-IN": "কলা",
          "mni-IN": "লফোই",
        },
        correct: true,
      },
      {
        id: "opt-2",
        text: {
          "en-IN": "Flowers",
          "as-IN": "ফুল",
          "hi-IN": "फूल",
          "bn-IN": "ফুল",
          "mni-IN": "লৈরাং",
        },
        correct: false,
      },
    ],
  },
  {
    id: "vlg-102",
    level: 1,
    icon: "🌺",
    domain: "Direct Recall",
    story: {
      "en-IN": "Rina went out to the garden. She gently watered the flowers.",
      "as-IN": "ৰিনাই ফুলনি বাৰীলৈ ওলাই গৈছিল। তাই ফুলবোৰত পানী দিছিল।",
      "hi-IN": "रीना बगीचे में गई। उसने फूलों को प्यार से पानी दिया।",
      "bn-IN": "রিনা বাগানে গেল। সে ফুলগুলোতে আলতো করে জল দিল।",
      "mni-IN": "রিনানা লৈকোন্দা চৎখি। মহাক্না লৈরাংদা তপ্না ঈশিং তখি।",
    },
    question: {
      "en-IN": "Where did Rina go?",
      "as-IN": "ৰিনা ক’লৈ গৈছিল?",
      "hi-IN": "रीना कहाँ गई थी?",
      "bn-IN": "রিনা কোথায় গিয়েছিল?",
      "mni-IN": "রিনানা কদাইদা চৎখিবগে?",
    },
    options: [
      {
        id: "opt-1",
        text: {
          "en-IN": "Garden",
          "as-IN": "ফুলনি বাৰী",
          "hi-IN": "बगीचा",
          "bn-IN": "বাগান",
          "mni-IN": "লৈকোন",
        },
        correct: true,
      },
      {
        id: "opt-2",
        text: {
          "en-IN": "Market",
          "as-IN": "বজাৰ",
          "hi-IN": "बाज़ार",
          "bn-IN": "বাজার",
          "mni-IN": "কৈথেল",
        },
        correct: false,
      },
    ],
  },
  {
    id: "vlg-103",
    level: 1,
    icon: "☕",
    domain: "Direct Recall",
    story: {
      "en-IN": "Grandfather sat on the front veranda. He drank warm Assam tea.",
      "as-IN": "ককাদেউতাই ঘৰৰ বাৰান্দাত বহিছিল। তেওঁ গৰম চাহ খাইছিল।",
      "hi-IN": "दादाजी सामने वाले बरामदे में बैठे। उन्होंने गर्म असम चाय पी।",
      "bn-IN": "দাদামশাই বারান্দায় বসেছিলেন। তিনি গরম আসাম চা খেলেন।",
      "mni-IN": "ইপুনা মাঙগোলদা ফমখি। মহাক্না অশাংবা আসাম চা থাকখি।",
    },
    question: {
      "en-IN": "What did Grandfather drink?",
      "as-IN": "ককাদেউতাই কি খাইছিল?",
      "hi-IN": "दादाजी ने क्या पिया?",
      "bn-IN": "দাদামশাই কী খেলেন?",
      "mni-IN": "ইপুনা করি থাকখিবগে?",
    },
    options: [
      {
        id: "opt-1",
        text: {
          "en-IN": "Warm Tea",
          "as-IN": "গৰম চাহ",
          "hi-IN": "गर्म चाय",
          "bn-IN": "গরম চা",
          "mni-IN": "অশাংবা চা",
        },
        correct: true,
      },
      {
        id: "opt-2",
        text: {
          "en-IN": "Cold Water",
          "as-IN": "ঠাণ্ডা পানী",
          "hi-IN": "ठंडा पानी",
          "bn-IN": "ঠান্ডা জল",
          "mni-IN": "ঈশিং",
        },
        correct: false,
      },
    ],
  },
  {
    id: "vlg-104",
    level: 1,
    icon: "🦆",
    domain: "Direct Recall",
    story: {
      "en-IN": "Anil took a walk by the village pond. He saw two white ducks swimming.",
      "as-IN": "অনিলে গাঁৱৰ পুখুৰীৰ পাৰেৰে খোজ কাঢ়িছিল। তেওঁ দুটা বগা হাঁহ দেখিছিল।",
      "hi-IN": "अनिल गाँव के तालाब के पास टहलने गया। उसने तैरती हुई सफेद बत्तखें देखीं।",
      "bn-IN": "অনিল গ্রামের পুকুরপাড়ে হাঁটছিল। সে সাদা হাঁস সাঁতার কাটতে দেখল।",
      "mni-IN": "অনিলনা খুঙ্গংগী পুখ্রিদা খোঙচৎ চৎখি। মহাক্না ঙানু অনি ঈরোইবা উখি।",
    },
    question: {
      "en-IN": "What did Anil see at the pond?",
      "as-IN": "অনিলে পুখুৰীত কি দেখিছিল?",
      "hi-IN": "अनिल ने तालाब पर क्या देखा?",
      "bn-IN": "অনিল পুকুরে কী দেখেছিল?",
      "mni-IN": "অনিলনা পুখ্রিদা করি উখিবগে?",
    },
    options: [
      {
        id: "opt-1",
        text: {
          "en-IN": "White Ducks",
          "as-IN": "বগা হাঁহ",
          "hi-IN": "सफेद बत्तखें",
          "bn-IN": "সাদা হাঁস",
          "mni-IN": "ঙানু",
        },
        correct: true,
      },
      {
        id: "opt-2",
        text: {
          "en-IN": "Cows",
          "as-IN": "গৰু",
          "hi-IN": "गायें",
          "bn-IN": "গরু",
          "mni-IN": "শন",
        },
        correct: false,
      },
    ],
  },

  // ───────────────────────────────────────────────────────────────────────────
  // LEVEL 2: OBJECT & EVENT RECALL (3 Choices)
  // ───────────────────────────────────────────────────────────────────────────
  {
    id: "vlg-201",
    level: 2,
    icon: "⛵",
    domain: "Object Recall",
    story: {
      "en-IN": "Biren walked to the Brahmaputra riverbank in the early morning. He saw a wooden fishing boat resting on the sand.",
      "as-IN": "বীৰেনে ৰাতিপুৱাই নদীৰ ঘাটলৈ গৈছিল। তেওঁ বালিত এখন কাঠৰ নাৱ বন্ধা দেখিলে।",
      "hi-IN": "बीरेन सुबह-सुबह नदी किनारे टहलने गया। उसने रेत पर लकड़ी की नाव बंधी देखी।",
      "bn-IN": "বীরেন সকালবেলা নদী তীরে হাঁটতে গেল। সে বালিতে একটি কাঠের নৌকা দেখতে পেল।",
      "mni-IN": "বীরেননা নুমিৎথাংদা তুরেং তোর্বান্দা চৎখি। মহাক্না উগী হী অমা উখি।",
    },
    question: {
      "en-IN": "What did Biren see by the river?",
      "as-IN": "বীৰেনে নদীৰ ঘাটত কি দেখিছিল?",
      "hi-IN": "बीरेन ने नदी किनारे क्या देखा?",
      "bn-IN": "বীরেন নদী তীরে কী দেখেছিল?",
      "mni-IN": "বীরেননা তুরেং তোর্বান্দা করি উখিবগে?",
    },
    options: [
      {
        id: "opt-1",
        text: {
          "en-IN": "Wooden Boat",
          "as-IN": "কাঠৰ নাও",
          "hi-IN": "लकड़ी की नाव",
          "bn-IN": "কাঠের নৌকা",
          "mni-IN": "উগী হী",
        },
        correct: true,
      },
      {
        id: "opt-2",
        text: {
          "en-IN": "Bicycle",
          "as-IN": "চাইকেল",
          "hi-IN": "साइकिल",
          "bn-IN": "সাইকেল",
          "mni-IN": "সাইকল",
        },
        correct: false,
      },
      {
        id: "opt-3",
        text: {
          "en-IN": "Market Cart",
          "as-IN": "ঠেলা গাড়ী",
          "hi-IN": "ठेला गाड़ी",
          "bn-IN": "ঠেলাগাড়ি",
          "mni-IN": "গাড়ি",
        },
        correct: false,
      },
    ],
  },
  {
    id: "vlg-202",
    level: 2,
    icon: "🥬",
    domain: "Object Recall",
    story: {
      "en-IN": "Mina harvested fresh green spinach from the kitchen garden. She prepared a warm home lunch for her grandchildren.",
      "as-IN": "মিনাই বাৰীৰ পৰা সতেজ পালেং শাক তুলি আনিছিল। তাই নাতি-নাতিনীহঁতৰ বাবে দুপৰীয়াৰ সাজ প্ৰস্তুত কৰিলে।",
      "hi-IN": "मीना ने घर के बगीचे से ताज़ा पालक तोड़ी। उसने पोते-पोतियों के लिए दोपहर का भोजन बनाया।",
      "bn-IN": "মীনা রান্নাঘরের বাগান থেকে টাটকা পালং শাক তুলল। সে নাতি-নাতনিদের জন্য দুপুরের খাবার রাঁধল।",
      "mni-IN": "মিনানা লৈকোন্দগী অশেংবা পালক লোকখি। মহাক্না অঙাংশিংগীদমক নুমিৎয়ুংগী চাক শেমখি।",
    },
    question: {
      "en-IN": "What did Mina pick from the garden?",
      "as-IN": "মিনাই বাৰীৰ পৰা কি তুলিছিল?",
      "hi-IN": "मीना ने बगीचे से क्या तोड़ा?",
      "bn-IN": "মীনা বাগান থেকে কী তুলেছিল?",
      "mni-IN": "মিনানা লৈকোন্দগী করি লোকখিবগে?",
    },
    options: [
      {
        id: "opt-1",
        text: {
          "en-IN": "Fresh Spinach",
          "as-IN": "পালেং শাক",
          "hi-IN": "ताज़ा पालक",
          "bn-IN": "পালং শাক",
          "mni-IN": "অশেংবা পালক",
        },
        correct: true,
      },
      {
        id: "opt-2",
        text: {
          "en-IN": "Ripe Mangoes",
          "as-IN": "পকা আম",
          "hi-IN": "पके आम",
          "bn-IN": "পাকা আম",
          "mni-IN": "হৌজিবা হৈনোউ",
        },
        correct: false,
      },
      {
        id: "opt-3",
        text: {
          "en-IN": "Red Apples",
          "as-IN": "ৰঙা আপেল",
          "hi-IN": "लाल सेब",
          "bn-IN": "লাল আপেল",
          "mni-IN": "অঙাংবা সেও",
        },
        correct: false,
      },
    ],
  },
  {
    id: "vlg-203",
    level: 2,
    icon: "🍍",
    domain: "Object Recall",
    story: {
      "en-IN": "Uncle returned home from the weekly village haat. He brought a sweet juicy pineapple for the whole family.",
      "as-IN": "খুৰা সাপ্তাহিক গাঁৱৰ হাটৰ পৰা ঘৰলৈ ঘূৰি আহিল। তেওঁ পৰিয়ালৰ বাবে এটা মিঠা মাটিকঁঠাল আনিলে।",
      "hi-IN": "चाचा साप्ताहिक गाँव के बाज़ार से घर लौटे। वे पूरे परिवार के लिए एक मीठा अनानास लाए।",
      "bn-IN": "কাকা সাপ্তাহিক হাট থেকে বাড়ি ফিরলেন। তিনি পরিবারের সবার জন্য মিষ্টি আনারস নিয়ে এলেন।",
      "mni-IN": "ইখুরোনা চয়োলগী কৈথেলদগী য়ুমদা হল্লকখি। মহাক্না অহাম্বা কিহোম অমা পুদুনা লাকখি।",
    },
    question: {
      "en-IN": "What fruit did Uncle bring from the haat?",
      "as-IN": "খুৰাই হাটৰ পৰা কি ফল আনিছিল?",
      "hi-IN": "चाचा बाज़ार से कौन सा फल लाए?",
      "bn-IN": "কাকা হাট থেকে কোন ফল এনেছিলেন?",
      "mni-IN": "ইখুরোনা কৈথেলদগী করি হৈহৌ পুদুনা লাকখিবগে?",
    },
    options: [
      {
        id: "opt-1",
        text: {
          "en-IN": "Sweet Pineapple",
          "as-IN": "মিঠা মাটিকঁঠাল",
          "hi-IN": "मीठा अनानास",
          "bn-IN": "মিষ্টি আনারস",
          "mni-IN": "অহাম্বা কিহোম",
        },
        correct: true,
      },
      {
        id: "opt-2",
        text: {
          "en-IN": "Yellow Papaya",
          "as-IN": "অমিতা",
          "hi-IN": "पपीता",
          "bn-IN": "পেঁপে",
          "mni-IN": "অৱাথবী",
        },
        correct: false,
      },
      {
        id: "opt-3",
        text: {
          "en-IN": "Green Guava",
          "as-IN": "মধুৰিআম",
          "hi-IN": "अमरूद",
          "bn-IN": "পেয়ারা",
          "mni-IN": "পুম্পোল",
        },
        correct: false,
      },
    ],
  },

  // ───────────────────────────────────────────────────────────────────────────
  // LEVEL 3: CONTEXT & DETAIL RECALL (3-4 Choices)
  // ───────────────────────────────────────────────────────────────────────────
  {
    id: "vlg-301",
    level: 3,
    icon: "📘",
    domain: "Context Recall",
    story: {
      "en-IN": "Aarav walked across the paddy field to meet his friend Maya. Maya smiled and gifted him a blue notebook.",
      "as-IN": "আৰভে পথাৰৰ আলিয়েদি মায়াৰ ঘৰলৈ গৈছিল। মায়াই হাঁহি মাৰি তাক এখন নীলা বহী উপহাৰ দিলে।",
      "hi-IN": "आरव खेत की पगडंडी से होते हुए अपनी दोस्त माया से मिलने गया। माया ने मुस्कुराते हुए उसे एक नीली कॉपी भेंट की।",
      "bn-IN": "আরভ ধানের ক্ষেতের পথ ধরে বন্ধু মায়ার কাছে গেল। মায়া হেসে তাকে একটি নীল রঙের খাতা উপহার দিল।",
      "mni-IN": "আরভনা লম্থাংদা মায়াগা উনবা চৎখি। মায়ানা মিনোক লোয়ননা মহাকপু নীলা লাইরিক অমা খুদোল পীরকখি।",
    },
    question: {
      "en-IN": "What color was the notebook Maya gave Aarav?",
      "as-IN": "মায়াই আৰভক দিয়া বহীখনৰ ৰং কি আছিল?",
      "hi-IN": "माया ने आरव को जो कॉपी दी उसका रंग क्या था?",
      "bn-IN": "মায়া আরভকে যে খাতাটি উপহার দিয়েছিল তার রং কী ছিল?",
      "mni-IN": "মায়ানা আরভপু পীরকপা লাইরিক অদুগী মচু করিনো?",
    },
    options: [
      {
        id: "opt-1",
        text: {
          "en-IN": "Blue",
          "as-IN": "নীলা",
          "hi-IN": "नीला",
          "bn-IN": "নীল",
          "mni-IN": "নীলা",
        },
        correct: true,
      },
      {
        id: "opt-2",
        text: {
          "en-IN": "Red",
          "as-IN": "ৰঙা",
          "hi-IN": "लाल",
          "bn-IN": "লাল",
          "mni-IN": "অঙাংবা",
        },
        correct: false,
      },
      {
        id: "opt-3",
        text: {
          "en-IN": "Yellow",
          "as-IN": "হালধীয়া",
          "hi-IN": "पीला",
          "bn-IN": "হলুদ",
          "mni-IN": "য়াইঙং",
        },
        correct: false,
      },
      {
        id: "opt-4",
        text: {
          "en-IN": "Green",
          "as-IN": "সেউজীয়া",
          "hi-IN": "हरा",
          "bn-IN": "সবুজ",
          "mni-IN": "অশেংবা",
        },
        correct: false,
      },
    ],
  },
  {
    id: "vlg-302",
    level: 3,
    icon: "🧣",
    domain: "Context Recall",
    story: {
      "en-IN": "Grandmother sat near the sunny courtyard after breakfast. She was lovingly weaving a red and white cotton gamosa.",
      "as-IN": "আইতাই পুৱাৰ চাহ খাই চোতালৰ ৰ’দত বহিছিল। তেওঁ মৰমেৰে এখন ৰঙা-বগা ফুলাম গামোচা বৈ আছিল।",
      "hi-IN": "दादी नाश्ते के बाद धूप वाले आँगन में बैठीं। वे प्यार से लाल और सफेद सूती गामोसा बुन रही थीं।",
      "bn-IN": "ঠাকুমা সকালের জলখাবারের পর রোদের উঠোনে বসলেন। তিনি যত্নে একটি লাল ও সাদা গামোসা বুনছিলেন।",
      "mni-IN": "ইবেনা নুমিৎ থোকপা মফমদা ফমখি। মহাক্না অঙাংবা অমসুং অঙৌবা গামোচা অমা শারে।",
    },
    question: {
      "en-IN": "What was Grandmother weaving in the courtyard?",
      "as-IN": "আইতাই চোতালত বহি কি বৈ আছিল?",
      "hi-IN": "दादी आँगन में बैठकर क्या बुन रही थीं?",
      "bn-IN": "ঠাকুমা উঠোনে বসে কী বুনছিলেন?",
      "mni-IN": "ইবেনা মফমদুদা করি শারিবা?",
    },
    options: [
      {
        id: "opt-1",
        text: {
          "en-IN": "Cotton Gamosa",
          "as-IN": "ফুলাম গামোচা",
          "hi-IN": "सूती गामोसा",
          "bn-IN": "সুতির গামোসা",
          "mni-IN": "গামোচা",
        },
        correct: true,
      },
      {
        id: "opt-2",
        text: {
          "en-IN": "Bamboo Basket",
          "as-IN": "বাঁহৰ খৰাহী",
          "hi-IN": "बाँस की टोकरी",
          "bn-IN": "বাঁশের ঝুড়ি",
          "mni-IN": "ৱাগী খোঙচৎ",
        },
        correct: false,
      },
      {
        id: "opt-3",
        text: {
          "en-IN": "Woolen Shawl",
          "as-IN": "উনৰ চাদৰ",
          "hi-IN": "ऊनी शॉल",
          "bn-IN": "উলের শাল",
          "mni-IN": "ফি",
        },
        correct: false,
      },
    ],
  },
  {
    id: "vlg-303",
    level: 3,
    icon: "🔔",
    domain: "Context Recall",
    story: {
      "en-IN": "In the cool evening, Father walked under the bamboo groves. From the nearby village prayer hall, he heard the temple bell chime.",
      "as-IN": "সন্ধিয়া দেউতাই বাঁহনিৰ তলৰ বাটেৰে খোজ কাঢ়িছিল। ওচৰৰ নামঘৰৰ পৰা তেওঁ কাঁহৰ ঘণ্টাৰ শব্দ শুনিলে।",
      "hi-IN": "ठंडी शाम में पिताजी बाँस के पेड़ों के नीचे टहल रहे थे। पास के मंदिर से उन्हें घंटी बजने की आवाज़ सुनाई दी।",
      "bn-IN": "শীতল সন্ধ্যায় বাবা বাঁশঝাড়ের পথ দিয়ে হাঁটছিলেন। পাশের উপাসনালয় থেকে তিনি ঘণ্টার মিষ্টি ধ্বনি শুনলেন।",
      "mni-IN": "নুমিদাংদা ইপানা ৱাম্বী মখাদা খোঙচৎ চৎখি। লায়নিংথাউ শংদগী মহাক্না ঘণ্টার খোন্থাং তারি।",
    },
    question: {
      "en-IN": "What sound did Father hear in the evening?",
      "as-IN": "দেউতাই গধূলি কিহৰ শব্দ শুনিছিল?",
      "hi-IN": "पिताजी ने शाम को किस चीज़ की आवाज़ सुनी?",
      "bn-IN": "বাবা সন্ধ্যায় কীসের শব্দ শুনেছিলেন?",
      "mni-IN": "ইপানা নুমিদাংদা করিগী খোন্থাং তারিবগে?",
    },
    options: [
      {
        id: "opt-1",
        text: {
          "en-IN": "Temple Bell",
          "as-IN": "নামঘৰৰ ঘণ্টা",
          "hi-IN": "मंदिर की घंटी",
          "bn-IN": "মন্দিরের ঘণ্টা",
          "mni-IN": "ঘণ্টার খোন্থাং",
        },
        correct: true,
      },
      {
        id: "opt-2",
        text: {
          "en-IN": "River Waves",
          "as-IN": "নদীৰ ঢৌ",
          "hi-IN": "नदी की लहरें",
          "bn-IN": "নদীর ঢেউ",
          "mni-IN": "তুরেংগী ঈশিং",
        },
        correct: false,
      },
      {
        id: "opt-3",
        text: {
          "en-IN": "Rain Drops",
          "as-IN": "বৰষুণৰ টোপাল",
          "hi-IN": "बारिश की बूँदें",
          "bn-IN": "বৃষ্টির ফোঁটা",
          "mni-IN": "নোং",
        },
        correct: false,
      },
      {
        id: "opt-4",
        text: {
          "en-IN": "Train Whistle",
          "as-IN": "ৰে’লৰ হুইচেল",
          "hi-IN": "ट्रेन की सीटी",
          "bn-IN": "ট্রেনের বাঁশি",
          "mni-IN": "রেলগী হুইসল",
        },
        correct: false,
      },
    ],
  },
];

export function getStoriesForLevel(level = 1) {
  const lvl = Math.max(1, Math.min(3, Number(level) || 1));
  const pool = VILLAGE_STORIES.filter((s) => s.level === lvl);
  return pool.length > 0 ? pool : VILLAGE_STORIES.filter((s) => s.level === 1);
}
