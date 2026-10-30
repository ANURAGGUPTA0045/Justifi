import { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'

const LANGUAGES = ['English', 'Hindi', 'Marathi']
const DEFAULT_MAX_FILE_BYTES = 8 * 1024 * 1024

const COPY = {
  English: {
    navHome: 'Dashboard',
    navAssistant: 'AI Legal Assistant',
    navDocument: 'Document Explainer',
    navExplore: 'Explore Laws',
    navSources: 'Legal Sources',
    navPrivacy: 'Privacy Center',
    navSettings: 'Settings',
    welcome: 'Legal clarity, one step at a time.',
    welcomeText: 'Understand Indian legal information with clear explanations connected to the sources available to JustiFi.',
    shortcuts: 'Your workspace',
    recent: 'Recent conversations',
    recentEmpty: 'No conversations yet. Your current session conversations will appear here.',
    service: 'Service status',
    workspace: 'WORKSPACE',
    preferences: 'PREFERENCES',
    language: 'Language',
    act: 'Act',
    section: 'Section',
    sourceType: 'Source type',
    jurisdictionLabel: 'Jurisdiction',
    publicationDate: 'Publication date',
    effectiveDate: 'Effective date',
    amendment: 'Amendment',
    records: 'records',
    verifiedRecord: 'Verified record',
    needsReview: 'Needs review',
    refresh: 'Refresh',
    user: 'YOU',
    messages: 'messages',
    currentSession: 'Current browser session only. Not private on a shared device.',
    redactionPatterns: 'patterns redacted',
    consentReview: 'PRIVACY REVIEW',
    externalAi: 'External AI processing',
    temporaryDocs: 'Temporary documents',
    conversationPrivacy: 'Accounts and chat history',
    processingLimitations: 'Processing limitations',
    redactionSetting: 'PII redaction is always active for supported patterns and cannot be disabled.',
    on: 'Always on',
    assistantTitle: 'Ask a legal question',
    assistantDescription: 'Ask in everyday language. Answers are generated only when legal passages can be retrieved.',
    question: 'Your question',
    answerLanguage: 'Response language',
    jurisdiction: 'State or jurisdiction (optional)',
    timeframe: 'Relevant date or period (optional)',
    ask: 'Get an explanation',
    asking: 'Searching legal sources…',
    newChat: 'New conversation',
    clearHistory: 'Clear session history',
    sources: 'Retrieved legal sources',
    noSources: 'No matching source records were found.',
    documentTitle: 'Understand a legal document',
    documentDescription: 'Upload a PDF, DOCX, or TXT file. Review extracted text and detected identifiers before sending only the redacted text for AI analysis.',
    selectFile: 'Choose a document',
    preview: 'Extract text and review privacy',
    redactionPreview: 'Show redacted preview',
    originalPreview: 'Show original preview',
    confirmAi: 'I agree to send the redacted document text and matching legal passages to the external AI provider for analysis.',
    analyze: 'Confirm & run AI analysis',
    analyzing: 'Analyzing document…',
    clear: 'Clear document',
    detectedDates: 'Dates found in document',
    noDates: 'No supported explicit date format was found.',
    extractedText: 'Extracted document text',
    analysis: 'Plain-language interpretation',
    overview: 'Overview',
    clauses: 'Important clauses',
    terms: 'Legal terms',
    obligations: 'Stated obligations',
    rights: 'Rights or remedies stated',
    questions: 'Questions to clarify',
    limitations: 'Important limitations',
    confirmDate: 'I have checked this date',
    dateReview: 'Review or correct this date',
    confirmDatesFirst: 'Review and confirm every detected date before analysis.',
    sourcesTitle: 'Explore legal sources',
    sourcesDescription: 'Browse and search records currently stored in the legal-source database. Availability depends on the configured database.',
    searchSources: 'Search title, Act, section, or text',
    search: 'Search',
    verification: 'Verification status',
    allStatuses: 'All statuses',
    jurisdictionFilter: 'Jurisdiction',
    anyJurisdiction: 'Any jurisdiction',
    page: 'Page',
    previous: 'Previous',
    next: 'Next',
    sourceDetails: 'Source passage',
    explainThis: 'Ask the assistant about this passage',
    notAvailable: 'Not available',
    privacyTitle: 'Privacy Center',
    settingsTitle: 'Settings',
    preferredLanguage: 'Preferred language',
    darkTheme: 'Dark theme',
    privacyExplain: 'Privacy and data handling',
    aiTransmission: 'When you ask a question or confirm document analysis, redacted question/document text and retrieved legal passages are sent to the configured AI provider. The provider may process that data under its own terms.',
    noAuth: 'There are no user accounts or authentication. Conversations are kept only in this open browser session and are not isolated for multiple users on a shared device.',
    notStored: 'The backend does not persist questions, documents, or chat messages. A pending document preview is kept temporarily in backend memory and expires after 15 minutes; clearing it removes that preview from this process.',
    piiLimits: 'Pattern-based redaction covers common emails, Indian mobile numbers, PAN-like strings, and 12-digit ID patterns. It may miss names, addresses, context-specific identifiers, and other sensitive information. Review the redacted preview before consent.',
    noOcr: 'Scanned PDFs are not OCR processed. No reminders, legal updates, account-level settings, or official live-source verification are enabled.',
    disclaimer: 'General legal information, not legal advice. Verify important questions with an authoritative source or qualified legal professional.',
    loading: 'Loading…',
    serviceUnavailable: 'Service unavailable',
    databaseUnavailable: 'Database unavailable',
    databaseAvailable: 'Local SQLite database ready',
    aiUnavailable: 'AI provider not configured',
    aiKeyConfigured: 'AI key present; provider availability is not checked',
    cleanupError: 'The temporary document could not be cleared from the server.',
    emptyDocuments: 'No source documents are available yet.',
    emptyConversations: 'No saved conversations in this browser session.',
    error: 'Something went wrong.',
  },
  Hindi: {
    navHome: 'डैशबोर्ड',
    navAssistant: 'AI कानूनी सहायक',
    navDocument: 'दस्तावेज़ समझें',
    navExplore: 'कानून खोजें',
    navSources: 'कानूनी स्रोत',
    navPrivacy: 'गोपनीयता केंद्र',
    navSettings: 'सेटिंग्स',
    welcome: 'कानून को समझें, एक कदम में।',
    welcomeText: 'JustiFi में उपलब्ध स्रोतों से जुड़े स्पष्ट स्पष्टीकरण के साथ भारतीय कानूनी जानकारी समझें।',
    shortcuts: 'आपका कार्यक्षेत्र',
    recent: 'हाल की बातचीत',
    recentEmpty: 'अभी कोई बातचीत नहीं है। इस ब्राउज़र सत्र की बातचीत यहाँ दिखेगी।',
    service: 'सेवा की स्थिति',
    workspace: 'कार्यक्षेत्र',
    preferences: 'प्राथमिकताएँ',
    language: 'भाषा',
    act: 'अधिनियम',
    section: 'धारा',
    sourceType: 'स्रोत का प्रकार',
    jurisdictionLabel: 'क्षेत्र',
    publicationDate: 'प्रकाशन तिथि',
    effectiveDate: 'प्रभावी तिथि',
    amendment: 'संशोधन',
    records: 'रिकॉर्ड',
    verifiedRecord: 'सत्यापित रिकॉर्ड',
    needsReview: 'जाँच आवश्यक',
    refresh: 'रीफ़्रेश करें',
    user: 'आप',
    messages: 'संदेश',
    currentSession: 'केवल वर्तमान ब्राउज़र सत्र। साझा डिवाइस पर निजी नहीं।',
    redactionPatterns: 'पहचान पैटर्न छिपाए',
    consentReview: 'गोपनीयता जाँच',
    externalAi: 'बाहरी AI प्रक्रिया',
    temporaryDocs: 'अस्थायी दस्तावेज़',
    conversationPrivacy: 'खाते और बातचीत इतिहास',
    processingLimitations: 'प्रक्रिया सीमाएँ',
    redactionSetting: 'समर्थित पहचान पैटर्न का छिपाव हमेशा चालू है और बंद नहीं किया जा सकता।',
    on: 'हमेशा चालू',
    assistantTitle: 'कानूनी सवाल पूछें',
    assistantDescription: 'आम भाषा में पूछें। उत्तर तभी बनेगा जब कानूनी अंश मिलेंगे।',
    question: 'आपका सवाल',
    answerLanguage: 'उत्तर की भाषा',
    jurisdiction: 'राज्य या क्षेत्र (वैकल्पिक)',
    timeframe: 'प्रासंगिक तारीख या अवधि (वैकल्पिक)',
    ask: 'स्पष्टीकरण पाएँ',
    asking: 'कानूनी स्रोत खोजे जा रहे हैं…',
    newChat: 'नई बातचीत',
    clearHistory: 'इस सत्र का इतिहास मिटाएँ',
    sources: 'प्राप्त कानूनी स्रोत',
    noSources: 'मेल खाते स्रोत रिकॉर्ड नहीं मिले।',
    documentTitle: 'कानूनी दस्तावेज़ समझें',
    documentDescription: 'PDF, DOCX या TXT अपलोड करें। AI विश्लेषण से पहले निकाले गए पाठ और पहचाने गए विवरण देखें।',
    selectFile: 'दस्तावेज़ चुनें',
    preview: 'पाठ निकालें और गोपनीयता जाँचें',
    redactionPreview: 'छिपाया गया पाठ दिखाएँ',
    originalPreview: 'मूल पाठ दिखाएँ',
    confirmAi: 'मैं विश्लेषण के लिए छिपाए गए दस्तावेज़ पाठ और मेल खाते कानूनी अंश बाहरी AI सेवा को भेजने की सहमति देता/देती हूँ।',
    analyze: 'सहमति दें और विश्लेषण करें',
    analyzing: 'दस्तावेज़ का विश्लेषण हो रहा है…',
    clear: 'दस्तावेज़ हटाएँ',
    detectedDates: 'दस्तावेज़ में मिली तारीखें',
    noDates: 'समर्थित स्पष्ट तारीख प्रारूप नहीं मिला।',
    extractedText: 'दस्तावेज़ से निकला पाठ',
    analysis: 'सरल भाषा में व्याख्या',
    overview: 'सारांश',
    clauses: 'महत्वपूर्ण धाराएँ',
    terms: 'कानूनी शब्द',
    obligations: 'स्पष्ट दायित्व',
    rights: 'बताए गए अधिकार या उपाय',
    questions: 'स्पष्ट करने योग्य प्रश्न',
    limitations: 'महत्वपूर्ण सीमाएँ',
    confirmDate: 'मैंने यह तारीख जाँच ली है',
    dateReview: 'तारीख देखें या सुधारें',
    confirmDatesFirst: 'विश्लेषण से पहले हर मिली तारीख की जाँच और पुष्टि करें।',
    sourcesTitle: 'कानूनी स्रोत खोजें',
    sourcesDescription: 'कानूनी स्रोत डेटाबेस में मौजूद रिकॉर्ड खोजें। उपलब्धता डेटाबेस पर निर्भर है।',
    searchSources: 'शीर्षक, अधिनियम, धारा या पाठ खोजें',
    search: 'खोजें',
    verification: 'सत्यापन स्थिति',
    allStatuses: 'सभी स्थितियाँ',
    jurisdictionFilter: 'क्षेत्र',
    anyJurisdiction: 'कोई भी क्षेत्र',
    page: 'पृष्ठ',
    previous: 'पिछला',
    next: 'अगला',
    sourceDetails: 'स्रोत अंश',
    explainThis: 'इस अंश के बारे में सहायक से पूछें',
    notAvailable: 'उपलब्ध नहीं',
    privacyTitle: 'गोपनीयता केंद्र',
    settingsTitle: 'सेटिंग्स',
    preferredLanguage: 'पसंदीदा भाषा',
    darkTheme: 'डार्क थीम',
    privacyExplain: 'गोपनीयता और डेटा',
    aiTransmission: 'सवाल या दस्तावेज़ विश्लेषण की पुष्टि पर, छिपाया गया पाठ और प्राप्त कानूनी अंश चुने गए बाहरी AI प्रदाता को भेजे जाते हैं।',
    noAuth: 'उपयोगकर्ता खाते या प्रमाणीकरण नहीं हैं। बातचीत केवल खुले ब्राउज़र सत्र में रहती है और साझा डिवाइस पर अलग-अलग उपयोगकर्ताओं के लिए सुरक्षित रूप से अलग नहीं है।',
    notStored: 'बैकएंड सवाल, दस्तावेज़ या बातचीत सहेजता नहीं है। लंबित दस्तावेज़ पूर्वावलोकन बैकएंड की मेमोरी में अस्थायी रूप से रहता है और 15 मिनट में समाप्त हो जाता है।',
    piiLimits: 'नियम-आधारित छिपाव आम ईमेल, भारतीय मोबाइल, PAN-जैसी और 12-अंकीय ID पहचानता है। नाम, पते और अन्य संवेदनशील जानकारी छूट सकती है। सहमति से पहले छिपाया पाठ देखें।',
    noOcr: 'स्कैन किए गए PDF पर OCR नहीं होता। रिमाइंडर, कानूनी अपडेट, खाते की सेटिंग या सरकारी स्रोत का लाइव सत्यापन सक्रिय नहीं है।',
    disclaimer: 'यह सामान्य कानूनी जानकारी है, कानूनी सलाह नहीं। महत्वपूर्ण बातों को आधिकारिक स्रोत या योग्य वकील से जाँचें।',
    loading: 'लोड हो रहा है…',
    serviceUnavailable: 'सेवा उपलब्ध नहीं',
    databaseUnavailable: 'डेटाबेस उपलब्ध नहीं',
    databaseAvailable: 'स्थानीय SQLite डेटाबेस तैयार है',
    aiUnavailable: 'AI सेवा कॉन्फ़िगर नहीं है',
    aiKeyConfigured: 'AI कुंजी मौजूद है; प्रदाता की उपलब्धता जाँची नहीं गई है',
    cleanupError: 'अस्थायी दस्तावेज़ सर्वर से हटाया नहीं जा सका।',
    emptyDocuments: 'अभी कोई स्रोत दस्तावेज़ उपलब्ध नहीं है।',
    emptyConversations: 'इस ब्राउज़र सत्र में कोई बातचीत नहीं है।',
    error: 'कुछ गड़बड़ हुई।',
  },
  Marathi: {
    navHome: 'डॅशबोर्ड',
    navAssistant: 'AI कायदेशीर सहाय्यक',
    navDocument: 'दस्तऐवज समजून घ्या',
    navExplore: 'कायदे शोधा',
    navSources: 'कायदेशीर स्रोत',
    navPrivacy: 'गोपनीयता केंद्र',
    navSettings: 'सेटिंग्ज',
    welcome: 'कायदा समजून घ्या, एका वेळी एक पाऊल.',
    welcomeText: 'JustiFi मध्ये उपलब्ध स्रोतांशी जोडलेले स्पष्ट स्पष्टीकरण मिळवा.',
    shortcuts: 'तुमचे कार्यक्षेत्र',
    recent: 'अलीकडील संभाषणे',
    recentEmpty: 'अजून संभाषण नाही. या ब्राउझर सत्रातील संभाषणे येथे दिसतील.',
    service: 'सेवेची स्थिती',
    workspace: 'कार्यस्थान',
    preferences: 'प्राधान्ये',
    language: 'भाषा',
    act: 'कायदा',
    section: 'कलम',
    sourceType: 'स्रोत प्रकार',
    jurisdictionLabel: 'कार्यक्षेत्र',
    publicationDate: 'प्रकाशन तारीख',
    effectiveDate: 'अंमल तारीख',
    amendment: 'दुरुस्ती',
    records: 'नोंदी',
    verifiedRecord: 'पडताळलेली नोंद',
    needsReview: 'पुनरावलोकन आवश्यक',
    refresh: 'रीफ्रेश करा',
    user: 'तुम्ही',
    messages: 'संदेश',
    currentSession: 'फक्त सध्याचे ब्राउझर सत्र. सामायिक उपकरणावर खाजगी नाही.',
    redactionPatterns: 'ओळख नमुने लपवले',
    consentReview: 'गोपनीयता तपासणी',
    externalAi: 'बाह्य AI प्रक्रिया',
    temporaryDocs: 'तात्पुरते दस्तऐवज',
    conversationPrivacy: 'खाती आणि संभाषण इतिहास',
    processingLimitations: 'प्रक्रिया मर्यादा',
    redactionSetting: 'समर्थित ओळख नमुन्यांचे लपवणे नेहमी सुरू असते आणि बंद करता येत नाही.',
    on: 'नेहमी सुरू',
    assistantTitle: 'कायदेशीर प्रश्न विचारा',
    assistantDescription: 'सोप्या भाषेत विचारा. कायदेशीर उतारे मिळाल्यावरच उत्तर तयार केले जाते.',
    question: 'तुमचा प्रश्न',
    answerLanguage: 'उत्तराची भाषा',
    jurisdiction: 'राज्य किंवा कार्यक्षेत्र (ऐच्छिक)',
    timeframe: 'संबंधित तारीख किंवा कालावधी (ऐच्छिक)',
    ask: 'स्पष्टीकरण मिळवा',
    asking: 'कायदेशीर स्रोत शोधत आहे…',
    newChat: 'नवे संभाषण',
    clearHistory: 'या सत्राचा इतिहास पुसा',
    sources: 'मिळालेले कायदेशीर स्रोत',
    noSources: 'जुळणारे स्रोत नोंदी सापडल्या नाहीत.',
    documentTitle: 'कायदेशीर दस्तऐवज समजून घ्या',
    documentDescription: 'PDF, DOCX किंवा TXT अपलोड करा. AI विश्लेषणापूर्वी काढलेला मजकूर आणि ओळखलेली माहिती तपासा.',
    selectFile: 'दस्तऐवज निवडा',
    preview: 'मजकूर काढा आणि गोपनीयता तपासा',
    redactionPreview: 'लपवलेला मजकूर दाखवा',
    originalPreview: 'मूळ मजकूर दाखवा',
    confirmAi: 'विश्लेषणासाठी लपवलेला दस्तऐवज मजकूर आणि जुळणारे कायदेशीर उतारे बाह्य AI सेवेकडे पाठवण्यास मी संमती देतो/देते.',
    analyze: 'संमती द्या आणि विश्लेषण करा',
    analyzing: 'दस्तऐवजाचे विश्लेषण सुरू आहे…',
    clear: 'दस्तऐवज काढा',
    detectedDates: 'दस्तऐवजात आढळलेल्या तारखा',
    noDates: 'समर्थित स्पष्ट तारीख नमुना आढळला नाही.',
    extractedText: 'दस्तऐवजातून काढलेला मजकूर',
    analysis: 'सोप्या भाषेतील स्पष्टीकरण',
    overview: 'आढावा',
    clauses: 'महत्त्वाची कलमे',
    terms: 'कायदेशीर संज्ञा',
    obligations: 'स्पष्ट नमूद केलेल्या जबाबदाऱ्या',
    rights: 'नमूद केलेले हक्क किंवा उपाय',
    questions: 'स्पष्ट करावयाचे प्रश्न',
    limitations: 'महत्त्वाच्या मर्यादा',
    confirmDate: 'मी ही तारीख तपासली आहे',
    dateReview: 'तारीख तपासा किंवा दुरुस्त करा',
    confirmDatesFirst: 'विश्लेषणापूर्वी प्रत्येक आढळलेली तारीख तपासा आणि निश्चित करा.',
    sourcesTitle: 'कायदेशीर स्रोत शोधा',
    sourcesDescription: 'कायदेशीर स्रोत डेटाबेसमधील नोंदी शोधा. उपलब्धता डेटाबेसवर अवलंबून आहे.',
    searchSources: 'शीर्षक, कायदा, कलम किंवा मजकूर शोधा',
    search: 'शोधा',
    verification: 'पडताळणी स्थिती',
    allStatuses: 'सर्व स्थिती',
    jurisdictionFilter: 'कार्यक्षेत्र',
    anyJurisdiction: 'कोणतेही कार्यक्षेत्र',
    page: 'पृष्ठ',
    previous: 'मागील',
    next: 'पुढील',
    sourceDetails: 'स्रोत उतारा',
    explainThis: 'या उताऱ्याबद्दल सहाय्यकाला विचारा',
    notAvailable: 'उपलब्ध नाही',
    privacyTitle: 'गोपनीयता केंद्र',
    settingsTitle: 'सेटिंग्ज',
    preferredLanguage: 'प्राधान्य भाषा',
    darkTheme: 'गडद थीम',
    privacyExplain: 'गोपनीयता आणि डेटा',
    aiTransmission: 'प्रश्न किंवा दस्तऐवज विश्लेषणाची पुष्टी केल्यावर, लपवलेला मजकूर आणि मिळालेले कायदेशीर उतारे बाह्य AI प्रदात्याकडे पाठवले जातात.',
    noAuth: 'वापरकर्ता खाती किंवा प्रमाणीकरण नाही. संभाषणे फक्त उघड्या ब्राउझर सत्रात राहतात आणि सामायिक उपकरणावर वापरकर्त्यांसाठी सुरक्षितपणे वेगळी नसतात.',
    notStored: 'बॅकएंड प्रश्न, दस्तऐवज किंवा संभाषणे साठवत नाही. प्रलंबित दस्तऐवज पूर्वावलोकन बॅकएंड मेमरीमध्ये तात्पुरते राहते आणि १५ मिनिटांनी संपते.',
    piiLimits: 'नमुना-आधारित लपवणे सामान्य ईमेल, भारतीय मोबाइल, PAN-सदृश आणि १२-अंकी ID ओळखते. नावे, पत्ते किंवा इतर माहिती सुटू शकते. संमतीपूर्वी लपवलेला मजकूर तपासा.',
    noOcr: 'स्कॅन केलेल्या PDF साठी OCR नाही. स्मरणपत्रे, कायदेशीर अद्यतने, खाते-आधारित सेटिंग्ज किंवा सरकारी स्रोताची थेट पडताळणी सुरू नाही.',
    disclaimer: 'ही सामान्य कायदेशीर माहिती आहे, कायदेशीर सल्ला नाही. महत्त्वाची माहिती अधिकृत स्रोत किंवा पात्र वकिलाकडून तपासा.',
    loading: 'लोड होत आहे…',
    serviceUnavailable: 'सेवा उपलब्ध नाही',
    databaseUnavailable: 'डेटाबेस उपलब्ध नाही',
    databaseAvailable: 'स्थानिक SQLite डेटाबेस तयार आहे',
    aiUnavailable: 'AI सेवा कॉन्फिगर केलेली नाही',
    aiKeyConfigured: 'AI कळ उपलब्ध आहे; सेवा उपलब्धता तपासलेली नाही',
    cleanupError: 'तात्पुरता दस्तऐवज सर्व्हरवरून हटवता आला नाही.',
    emptyDocuments: 'अद्याप स्रोत दस्तऐवज उपलब्ध नाहीत.',
    emptyConversations: 'या ब्राउझर सत्रात संभाषण नाही.',
    error: 'काहीतरी चूक झाली.',
  },
}

function getErrorMessage(payload, fallback) {
  const detail = payload?.detail
  if (typeof detail === 'string') return detail
  if (detail?.message) return detail.message
  return fallback
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options)
  let payload
  try {
    payload = await response.json()
  } catch {
    payload = null
  }
  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        payload,
        response.status >= 500
          ? 'The service is temporarily unavailable.'
          : 'Please check the request and try again.',
      ),
    )
  }
  return payload
}

function ServiceBadge({ status, t }) {
  const database = status?.sqlite || 'checking'
  const ai = status?.ai || 'checking'
  return (
    <div className="service-badge is-warning">
      <span className="service-dot" />
      {database !== 'available'
        ? t('databaseUnavailable')
        : ai === 'configured'
          ? t('aiKeyConfigured')
          : t('aiUnavailable')}
    </div>
  )
}

function Sidebar({ page, setPage, language, setLanguage, t, onNewChat, onOpenPrivacy }) {
  const nav = [
    ['home', t('navHome'), '⌂'],
    ['assistant', t('navAssistant'), '✳'],
    ['document', t('navDocument'), '▤'],
    ['explore', t('navExplore'), '⌕'],
    ['sources', t('navSources'), '◫'],
  ]
  return (
    <aside className="sidebar">
      <a className="sidebar-brand" href="#home" onClick={(event) => {
        event.preventDefault()
        setPage('home')
      }}>
        <span className="brand-emblem">J</span>
        <span>JustiFi<small>LEGAL INTELLIGENCE</small></span>
      </a>
      <div className="sidebar-label">{t('workspace')}</div>
      <nav className="primary-nav" aria-label="Main navigation">
        {nav.map(([key, label, icon]) => (
          <button
            type="button"
            className={page === key ? 'nav-item active' : 'nav-item'}
            key={key}
            onClick={() => setPage(key)}
            aria-current={page === key ? 'page' : undefined}
          >
            <span className="nav-icon" aria-hidden="true">{icon}</span>
            <span>{label}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar-label more-label">{t('preferences')}</div>
      <nav className="primary-nav" aria-label="Privacy and settings">
        <button type="button" className={page === 'privacy' ? 'nav-item active' : 'nav-item'} onClick={onOpenPrivacy}>
          <span className="nav-icon" aria-hidden="true">◇</span><span>{t('navPrivacy')}</span>
        </button>
        <button type="button" className={page === 'settings' ? 'nav-item active' : 'nav-item'} onClick={() => setPage('settings')}>
          <span className="nav-icon" aria-hidden="true">⚙</span><span>{t('navSettings')}</span>
        </button>
      </nav>
      <div className="sidebar-bottom">
        <label htmlFor="app-language">{t('language')}</label>
        <select id="app-language" value={language} onChange={(event) => setLanguage(event.target.value)}>
          {LANGUAGES.map((item) => <option key={item}>{item}</option>)}
        </select>
        <button className="new-chat-button" type="button" onClick={onNewChat}>＋ {t('newChat')}</button>
        <p>{t('disclaimer')}</p>
      </div>
    </aside>
  )
}

function PageHeader({ eyebrow, title, description, children }) {
  return (
    <div className="page-header">
      <div>
        {eyebrow && <p className="page-eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {description && <p className="page-description">{description}</p>}
      </div>
      {children}
    </div>
  )
}

function EmptyState({ title, body }) {
  return (
    <div className="empty-state">
      <span aria-hidden="true">◇</span>
      <h3>{title}</h3>
      <p>{body}</p>
    </div>
  )
}

function Metadata({ citation, t }) {
  const fields = [
    [t('act'), citation.act_name],
    [t('section'), citation.section],
    [t('page'), citation.page],
    [t('sourceType'), citation.source_type],
    [t('jurisdictionLabel'), citation.jurisdiction],
    [t('publicationDate'), citation.publication_date],
    [t('effectiveDate'), citation.effective_date],
    [t('amendment'), citation.amendment_information],
  ]
  return (
    <dl className="metadata-grid">
      {fields.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value ?? t('notAvailable')}</dd>
        </div>
      ))}
    </dl>
  )
}

function AssistantPage({
  language,
  t,
  sessions,
  setSessions,
  activeSessionId,
  setActiveSessionId,
  jurisdiction,
  setJurisdiction,
  legalTimeframe,
  setLegalTimeframe,
  initialQuestion,
  clearInitialQuestion,
  onExplainSource,
}) {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const activeSession = sessions.find((session) => session.id === activeSessionId)
  const messages = activeSession?.messages || []
  const [question, setQuestion] = useState(initialQuestion)

  async function submitQuestion(event) {
    event.preventDefault()
    if (!question.trim() || isLoading) return
    const submittedQuestion = question.trim()
    const sessionId = activeSessionId || crypto.randomUUID()
    const priorMessages = messages.slice(-6)
    const newUserMessage = { role: 'user', content: submittedQuestion }
    setError('')
    setIsLoading(true)
    setQuestion('')
    if (!activeSessionId) setActiveSessionId(sessionId)

    try {
      const result = await requestJson('/api/legal/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: submittedQuestion,
          language,
          jurisdiction: jurisdiction.trim() || null,
          legal_timeframe: legalTimeframe.trim() || null,
          conversation_context: priorMessages,
        }),
      })
      const sessionMessages = [
        ...messages,
        newUserMessage,
        { role: 'assistant', content: result.answer, result },
      ]
      setSessions((previous) => {
        const existing = previous.find((session) => session.id === sessionId)
        if (existing) {
          return previous.map((session) => session.id === sessionId
            ? { ...session, messages: sessionMessages, updatedAt: Date.now() }
            : session)
        }
        return [
          { id: sessionId, title: submittedQuestion.slice(0, 60), messages: sessionMessages, updatedAt: Date.now() },
          ...previous,
        ]
      })
    } catch (requestError) {
      setQuestion(submittedQuestion)
      setError(requestError instanceof Error ? requestError.message : t('error'))
    } finally {
      setIsLoading(false)
    }
  }

  function startNew() {
    const id = crypto.randomUUID()
    setSessions((previous) => [
      { id, title: t('newChat'), messages: [], updatedAt: Date.now() },
      ...previous,
    ])
    setActiveSessionId(id)
    setError('')
    setQuestion('')
    clearInitialQuestion('')
  }

  function deleteSession(id) {
    setSessions((previous) => previous.filter((session) => session.id !== id))
    if (activeSessionId === id) setActiveSessionId(null)
  }

  return (
    <>
      <PageHeader eyebrow="JUSTIFI ASSISTANT" title={t('assistantTitle')} description={t('assistantDescription')}>
        <button className="button button-outline" type="button" onClick={startNew}>＋ {t('newChat')}</button>
      </PageHeader>
      <div className="assistant-layout">
        <aside className="conversation-panel panel">
          <div className="panel-title-row">
            <h2>{t('recent')}</h2>
            <button type="button" className="text-button" onClick={() => {
              setSessions([])
              setActiveSessionId(null)
            }}>{t('clearHistory')}</button>
          </div>
          {sessions.length === 0 ? (
            <p className="muted small">{t('recentEmpty')}</p>
          ) : (
            <ul className="conversation-list">
              {sessions.map((session) => (
                <li key={session.id}>
                  <button type="button" className={session.id === activeSessionId ? 'conversation-item selected' : 'conversation-item'} onClick={() => setActiveSessionId(session.id)}>
                    <span>{session.title || t('newChat')}</span>
                    <small>{session.messages.filter((message) => message.role === 'user').length} {t('messages')}</small>
                  </button>
                  <button type="button" className="icon-button" aria-label={`Delete ${session.title}`} onClick={() => deleteSession(session.id)}>×</button>
                </li>
              ))}
            </ul>
          )}
          <p className="session-note">{t('currentSession')}</p>
        </aside>
        <section className="assistant-panel panel">
          {messages.length > 0 && (
            <div className="chat-messages" aria-live="polite">
              {messages.map((message, index) => (
                <article className={`chat-message ${message.role}`} key={`${activeSessionId}-${index}`}>
                  <span className="message-label">{message.role === 'user' ? t('user') : 'JUSTIFI'}</span>
                  <p>{message.content}</p>
                  {message.result?.citations?.length > 0 && (
                    <SourceCards
                      citations={message.result.citations}
                      t={t}
                      onExplain={onExplainSource}
                    />
                  )}
                  {message.result?.limitations?.map((item) => <small className="message-limitation" key={item}>{item}</small>)}
                </article>
              ))}
            </div>
          )}
          {messages.length === 0 && (
            <EmptyState title={t('assistantTitle')} body={t('assistantDescription')} />
          )}
          {error && <div className="inline-error" role="alert">{error}</div>}
          {isLoading && <div className="loading-line" role="status">{t('asking')}</div>}
          <form className="assistant-form" onSubmit={submitQuestion}>
            <label htmlFor="legal-question">{t('question')}</label>
            <textarea id="legal-question" maxLength={4000} value={question} onChange={(event) => setQuestion(event.target.value)} rows={4} required />
            <div className="assistant-options">
              <label>{t('jurisdiction')}<input maxLength={120} value={jurisdiction} onChange={(event) => setJurisdiction(event.target.value)} /></label>
              <label>{t('timeframe')}<input maxLength={120} value={legalTimeframe} onChange={(event) => setLegalTimeframe(event.target.value)} /></label>
            </div>
            <div className="form-action-row">
              <span className="muted small">PII patterns are redacted before retrieval and AI processing.</span>
              <button className="button button-primary" type="submit" disabled={!question.trim() || isLoading}>{isLoading ? t('asking') : t('ask')} <span aria-hidden="true">→</span></button>
            </div>
          </form>
        </section>
      </div>
    </>
  )
}

function SourceCards({ citations, t, onExplain }) {
  return (
    <div className="chat-citations">
      {citations.map((citation) => (
        <article className="citation-card" key={citation.source_id}>
          <div className="citation-heading">
            <h3>{citation.title}</h3>
            <span className={`verification-pill ${citation.verification_status === 'verified' ? 'verified' : ''}`}>
            {citation.verification_status === 'verified' ? t('verifiedRecord') : t('needsReview')}
            </span>
          </div>
          <p className="citation-filename">{citation.source}</p>
          <Metadata citation={citation} t={t} />
          <div className="citation-actions">
            {citation.source_url && (
              <a href={citation.source_url} target="_blank" rel="noreferrer">Open source ↗</a>
            )}
            <button className="text-button" type="button" onClick={() => onExplain(citation)}> {t('explainThis')} </button>
          </div>
        </article>
      ))}
    </div>
  )
}

function DocumentPage({ language, t, onExplainSource, maxUploadBytes }) {
  const fileInput = useRef(null)
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [showRedacted, setShowRedacted] = useState(true)
  const [consent, setConsent] = useState(false)
  const [dates, setDates] = useState([])
  const [isExtracting, setIsExtracting] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [error, setError] = useState('')

  async function clearWorkflow() {
    let cleanupError = ''
    if (preview?.document_id) {
      try {
        const response = await fetch(`/api/documents/${preview.document_id}`, { method: 'DELETE' })
        if (!response.ok) cleanupError = t('cleanupError')
      } catch {
        cleanupError = t('cleanupError')
      }
    }
    if (cleanupError) {
      setError(cleanupError)
      return false
    }
    setFile(null)
    setPreview(null)
    setAnalysis(null)
    setDates([])
    setConsent(false)
    setError('')
    if (fileInput.current) fileInput.current.value = ''
    return true
  }

  async function createPreview() {
    if (!file) return
    if (file.size === 0) {
      setError('The selected file is empty.')
      return
    }
    if (file.size > maxUploadBytes) {
      setError(`The document exceeds the ${(maxUploadBytes / (1024 * 1024)).toFixed(0)} MiB upload limit.`)
      return
    }
    if (!await clearWorkflow()) return
    setFile(file)
    setIsExtracting(true)
    setError('')
    const form = new FormData()
    form.append('file', file)
    try {
      const data = await requestJson('/api/documents/preview', { method: 'POST', body: form })
      setPreview(data)
      setDates(data.dates.map((item) => ({ ...item, confirmed: false })))
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : t('error'))
    } finally {
      setIsExtracting(false)
    }
  }

  async function runAnalysis() {
    if (!preview || !consent || isAnalyzing || dates.some((item) => !item.confirmed)) return
    setIsAnalyzing(true)
    setError('')
    try {
      const data = await requestJson('/api/documents/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_id: preview.document_id,
          language,
          confirm_external_ai: consent,
          date_reviews: dates.map(({ source_text, date, confirmed, page }) => ({ source_text, date, confirmed, page })),
        }),
      })
      setAnalysis(data)
      setPreview(null)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : t('error'))
    } finally {
      setIsAnalyzing(false)
    }
  }

  function updateDate(index, patch) {
    setDates((previous) => previous.map((item, current) => current === index ? { ...item, ...patch } : item))
  }

  const previewText = preview
    ? (showRedacted ? preview.redacted_preview : preview.original_preview)
    : ''

  async function handleFileChange(event) {
    if (preview?.document_id) {
      try {
        const response = await fetch(`/api/documents/${preview.document_id}`, { method: 'DELETE' })
        if (!response.ok) throw new Error(t('cleanupError'))
      } catch {
        setError(t('cleanupError'))
        event.target.value = ''
        return
      }
    }
    setFile(event.target.files?.[0] || null)
    setPreview(null)
    setAnalysis(null)
    setDates([])
    setConsent(false)
    setError('')
  }

  return (
    <>
      <PageHeader eyebrow="DOCUMENT EXPLAINER" title={t('documentTitle')} description={t('documentDescription')} />
      <section className="panel document-upload-panel">
        <div className="document-drop">
          <div className="upload-symbol" aria-hidden="true">↑</div>
          <div>
            <h2>{t('selectFile')}</h2>
            <p>PDF, DOCX, or UTF-8 TXT · Maximum {(maxUploadBytes / (1024 * 1024)).toFixed(0)} MiB · Scanned PDF OCR is not available</p>
          </div>
          <input ref={fileInput} type="file" accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain" onChange={handleFileChange} />
        </div>
        {file && <div className="selected-file"><span>▤</span><strong>{file.name}</strong><span>{(file.size / 1024).toFixed(0)} KB</span></div>}
        {error && <div className="inline-error" role="alert">{error}</div>}
        <div className="form-action-row document-actions">
          <button className="button button-outline" type="button" onClick={clearWorkflow} disabled={isExtracting || isAnalyzing}>{t('clear')}</button>
          <button className="button button-primary" type="button" onClick={createPreview} disabled={!file || isExtracting || isAnalyzing}>{isExtracting ? t('loading') : t('preview')}</button>
        </div>
      </section>

      {preview && (
        <section className="panel document-review-panel">
          <div className="panel-title-row">
            <div>
              <p className="page-eyebrow">{t('consentReview')}</p>
              <h2>{preview.filename}</h2>
            </div>
            <span className="verification-pill">{preview.redaction_count} {t('redactionPatterns')}</span>
          </div>
          <div className="redaction-control">
            <span>Preview mode</span>
            <button className="button button-outline" type="button" aria-pressed={showRedacted} onClick={() => setShowRedacted((value) => !value)}>
              {showRedacted ? t('originalPreview') : t('redactionPreview')}
            </button>
          </div>
          <label className="field-label" htmlFor="extracted-preview">{t('extractedText')}</label>
          <textarea id="extracted-preview" className="document-preview" readOnly value={previewText} />
          {dates.length > 0 ? (
            <div className="date-review">
              <h3>{t('detectedDates')}</h3>
              {dates.map((item, index) => (
                <div className="date-review-row" key={`${item.source_text}-${item.page}-${index}`}>
                  <label>
                    <span>{t('dateReview')} · {item.source_text}</span>
                    <input value={item.date} onChange={(event) => updateDate(index, { date: event.target.value, confirmed: false })} maxLength={40} />
                    <small>{item.context}{item.page != null ? ` · Page ${item.page}` : ''}</small>
                  </label>
                  <label className="date-confirm"><input type="checkbox" checked={item.confirmed} onChange={(event) => updateDate(index, { confirmed: event.target.checked })} />{t('confirmDate')}</label>
                </div>
              ))}
              <p className="muted small">Dates are explicit text only. No statutory deadline is calculated; ambiguous formats require your review.</p>
            </div>
          ) : <p className="muted small">{t('noDates')}</p>}
          <label className="consent-row">
            <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} />
            <span>{t('confirmAi')}</span>
          </label>
          <div className="form-action-row document-actions">
            <button className="button button-outline" type="button" onClick={clearWorkflow}>{t('clear')}</button>
            <button className="button button-primary" type="button" onClick={runAnalysis} disabled={!consent || isAnalyzing || dates.some((item) => !item.confirmed)}>{isAnalyzing ? t('analyzing') : t('analyze')}</button>
          </div>
          {dates.some((item) => !item.confirmed) && <p className="muted small">{t('confirmDatesFirst')}</p>}
          {isAnalyzing && <p role="status" className="loading-line">{t('analyzing')}</p>}
        </section>
      )}

      {analysis && (
        <section className="panel analysis-panel">
          <div className="panel-title-row"><div><p className="page-eyebrow">AI ANALYSIS · {analysis.filename}</p><h2>{t('analysis')}</h2></div></div>
          <div className="analysis-overview"><h3>{t('overview')}</h3><p>{analysis.analysis.overview}</p></div>
          <AnalysisList title={t('clauses')} items={analysis.analysis.important_clauses} />
          <AnalysisList title={t('terms')} items={analysis.analysis.legal_terms} />
          <AnalysisList title={t('obligations')} items={analysis.analysis.obligations} />
          <AnalysisList title={t('rights')} items={analysis.analysis.rights_or_remedies} />
          <AnalysisList title={t('questions')} items={analysis.analysis.questions_to_clarify} />
          {analysis.dates.length > 0 && (
            <div className="analysis-dates">
              <h3>{t('detectedDates')}</h3>
              {analysis.dates.map((item) => <p key={`${item.source_text}-${item.page}`}>{item.date} · {item.context} · {item.confirmed_by_user ? 'Confirmed by user' : 'Please verify'}{item.page != null ? ` · Page ${item.page}` : ''}</p>)}
            </div>
          )}
          <AnalysisList title={t('limitations')} items={analysis.limitations} />
          {analysis.citations.length > 0 && <div className="analysis-sources"><h3>{t('sources')}</h3><SourceCards citations={analysis.citations} t={t} onExplain={onExplainSource} /></div>}
          <button className="button button-outline" type="button" onClick={() => setAnalysis(null)}>{t('clear')}</button>
        </section>
      )}
    </>
  )
}

function AnalysisList({ title, items }) {
  if (!items?.length) return null
  return <section className="analysis-list"><h3>{title}</h3><ul>{items.map((item, index) => <li key={`${title}-${index}`}>{item}</li>)}</ul></section>
}

function SourceExplorer({ page, t, onExplainSource }) {
  const [searchInput, setSearchInput] = useState('')
  const [query, setQuery] = useState('')
  const [verification, setVerification] = useState('')
  const [jurisdiction, setJurisdiction] = useState('')
  const [offset, setOffset] = useState(0)
  const [data, setData] = useState(null)
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const limit = 20

  const loadSources = useCallback(async () => {
    setLoading(true)
    setError('')
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
    if (query) params.set('query', query)
    if (verification) params.set('verification_status', verification)
    if (jurisdiction) params.set('jurisdiction', jurisdiction)
    try {
      const result = await requestJson(`/api/legal/sources?${params}`)
      setData(result)
    } catch (requestError) {
      setData(null)
      setError(requestError instanceof Error ? requestError.message : t('error'))
    } finally {
      setLoading(false)
    }
  }, [query, verification, jurisdiction, offset, t])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadSources()
    }, 0)
    return () => window.clearTimeout(timer)
  }, [loadSources])

  function search(event) {
    event.preventDefault()
    setOffset(0)
    setSelected(null)
    setLoading(true)
    setQuery(searchInput.trim())
  }

  async function openSource(item) {
    try {
      const full = await requestJson(`/api/legal/sources/${encodeURIComponent(item.id)}`)
      setSelected(full)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : t('error'))
    }
  }

  return (
    <>
      <PageHeader eyebrow={page === 'sources' ? 'SOURCE TRANSPARENCY' : 'LEGAL RESEARCH'} title={page === 'sources' ? t('sourcesTitle') : t('navExplore')} description={t('sourcesDescription')}>
        <button type="button" className="button button-outline" onClick={loadSources} disabled={loading}>{loading ? t('loading') : '↻ Refresh'}</button>
      </PageHeader>
      <section className="panel source-search-panel">
        <form className="source-search-form" onSubmit={search}>
          <label className="sr-only" htmlFor="source-query">{t('searchSources')}</label>
          <input id="source-query" value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder={t('searchSources')} maxLength={160} />
          <select aria-label={t('verification')} value={verification} onChange={(event) => { setOffset(0); setVerification(event.target.value) }}>
            <option value="">{t('allStatuses')}</option>
            <option value="verified">verified</option>
            <option value="needs_review">needs_review</option>
            <option value="unverified">unverified</option>
          </select>
          <input aria-label={t('jurisdictionFilter')} placeholder={t('anyJurisdiction')} value={jurisdiction} onChange={(event) => { setOffset(0); setJurisdiction(event.target.value) }} maxLength={120} />
          <button className="button button-primary" type="submit">{t('search')}</button>
        </form>
      </section>
      {error && <div className="inline-error" role="alert">{error}</div>}
      {loading && <div className="loading-line" role="status">{t('loading')}</div>}
      {!loading && data?.items.length === 0 && <EmptyState title={t('emptyDocuments')} body={t('noSources')} />}
      <div className="source-explorer-grid">
        <section className="source-results">
          {data?.items.map((item) => (
            <article className={`source-record panel ${selected?.id === item.id ? 'selected' : ''}`} key={item.id}>
              <div className="citation-heading">
                <h2>{item.title}</h2>
                <span className={`verification-pill ${item.verification_status === 'verified' ? 'verified' : ''}`}>{item.verification_status || 'needs_review'}</span>
              </div>
              <p className="citation-filename">{item.source}</p>
              <Metadata citation={item} t={t} />
              <p className="source-snippet">{item.content?.slice(0, 340)}{item.content?.length > 340 ? '…' : ''}</p>
              <div className="citation-actions">
                <button className="text-button" type="button" onClick={() => openSource(item)}>{t('sourceDetails')} →</button>
                {item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer">Open source ↗</a>}
                <button className="text-button" type="button" onClick={() => onExplainSource(item)}>{t('explainThis')}</button>
              </div>
            </article>
          ))}
        </section>
        {selected && (
          <aside className="panel source-detail">
            <div className="panel-title-row"><h2>{t('sourceDetails')}</h2><button className="icon-button" type="button" aria-label="Close source details" onClick={() => setSelected(null)}>×</button></div>
            <h3>{selected.title}</h3>
            <p className="citation-filename">{selected.source}</p>
            <Metadata citation={selected} t={t} />
            <span className="verification-pill">{selected.verification_status || 'needs_review'}</span>
            <pre className="source-full-text">{selected.content || t('notAvailable')}</pre>
            {selected.source_url && <a href={selected.source_url} target="_blank" rel="noreferrer">Open source ↗</a>}
            <button className="button button-primary full-button" type="button" onClick={() => onExplainSource(selected)}>{t('explainThis')}</button>
          </aside>
        )}
      </div>
      {data && (
        <div className="pagination">
          <span>{t('page')} {Math.floor(offset / limit) + 1} · {data.total} records</span>
          <div>
            <button className="button button-outline" type="button" disabled={offset === 0 || loading} onClick={() => setOffset((value) => Math.max(0, value - limit))}>{t('previous')}</button>
            <button className="button button-outline" type="button" disabled={offset + limit >= data.total || loading} onClick={() => setOffset((value) => value + limit)}>{t('next')}</button>
          </div>
        </div>
      )}
    </>
  )
}

function Dashboard({ t, serviceStatus, sessions, setPage, setActiveSessionId }) {
  const shortcuts = [
    ['assistant', '✳', t('navAssistant'), t('assistantDescription')],
    ['document', '▤', t('navDocument'), t('documentDescription')],
    ['explore', '⌕', t('navExplore'), t('sourcesDescription')],
    ['sources', '◫', t('navSources'), t('sourcesDescription')],
  ]
  return (
    <>
      <section className="welcome-panel">
        <div>
          <p className="page-eyebrow">JUSTIFI · LEGAL INFORMATION</p>
          <h1>{t('welcome')}</h1>
          <p>{t('welcomeText')}</p>
        </div>
        <div className="welcome-mark" aria-hidden="true">J</div>
      </section>
      <div className="dashboard-status panel">
        <div><span className="dashboard-status-icon">●</span><div><h2>{t('service')}</h2><p>{serviceStatus?.sqlite === 'available' ? t('databaseAvailable') : t('databaseUnavailable')} · {serviceStatus?.ai === 'configured' ? t('aiKeyConfigured') : t('aiUnavailable')}</p></div></div>
      </div>
      <section className="dashboard-section">
        <div className="section-heading"><h2>{t('shortcuts')}</h2></div>
        <div className="feature-grid">
          {shortcuts.map(([key, icon, title, description]) => (
            <button className="feature-card panel" key={key} type="button" onClick={() => setPage(key)}>
              <span className="feature-icon">{icon}</span><span className="feature-title">{title}</span><span className="feature-description">{description}</span><span className="feature-arrow">→</span>
            </button>
          ))}
        </div>
      </section>
      <section className="dashboard-section">
        <div className="section-heading"><h2>{t('recent')}</h2><span className="muted small">This browser session only</span></div>
        {sessions.length === 0 ? <EmptyState title={t('emptyConversations')} body={t('recentEmpty')} /> : (
          <div className="recent-list">
            {sessions.slice(0, 4).map((session) => <button type="button" className="recent-item panel" key={session.id} onClick={() => { setActiveSessionId(session.id); setPage('assistant') }}><span className="recent-icon">↗</span><span><strong>{session.title}</strong><small>{new Date(session.updatedAt).toLocaleString()}</small></span><span>→</span></button>)}
          </div>
        )}
      </section>
    </>
  )
}

function PrivacyPage({ t }) {
  return (
    <>
      <PageHeader eyebrow="DATA TRANSPARENCY" title={t('privacyTitle')} description={t('privacyExplain')} />
      <div className="privacy-grid">
        {[
          ['PII redaction', t('piiLimits')],
          ['External AI processing', t('aiTransmission')],
          ['Temporary documents', t('notStored')],
          ['Accounts and chat history', t('noAuth')],
          ['Processing limitations', t('noOcr')],
        ].map(([title, body]) => <article className="panel privacy-detail-card" key={title}><span className="privacy-detail-icon">◇</span><h2>{title}</h2><p>{body}</p></article>)}
      </div>
      <aside className="disclaimer-panel">{t('disclaimer')}</aside>
    </>
  )
}

function SettingsPage({ language, setLanguage, darkTheme, setDarkTheme, t, setSessions, setActiveSessionId }) {
  return (
    <>
      <PageHeader eyebrow="PREFERENCES" title={t('settingsTitle')} description="Preferences are stored on this device only; there are no user accounts." />
      <section className="panel settings-panel">
        <label className="settings-row">
          <span><strong>{t('preferredLanguage')}</strong><small>Changes interface labels and the requested answer language.</small></span>
          <select value={language} onChange={(event) => setLanguage(event.target.value)}>{LANGUAGES.map((item) => <option key={item}>{item}</option>)}</select>
        </label>
        <label className="settings-row">
          <span><strong>{t('darkTheme')}</strong><small>Applies a local dark theme to this browser.</small></span>
          <input type="checkbox" checked={darkTheme} onChange={(event) => setDarkTheme(event.target.checked)} />
        </label>
        <div className="settings-row">
          <span><strong>Session conversation history</strong><small>Messages exist only in this open app session and are sent as limited context to the AI when you continue a conversation.</small></span>
          <button type="button" className="button button-outline" onClick={() => { setSessions([]); setActiveSessionId(null) }}>Clear now</button>
        </div>
        <div className="settings-row settings-info">
          <span><strong>Privacy controls</strong><small>PII redaction is always active for supported patterns and cannot be disabled.</small></span>
          <span className="setting-status">Always on</span>
        </div>
      </section>
    </>
  )
}

function App() {
  const [page, setPageState] = useState(() => {
    const initial = window.location.hash.slice(1)
    return ['home', 'assistant', 'document', 'explore', 'sources', 'privacy', 'settings'].includes(initial)
      ? initial
      : 'home'
  })
  const [language, setLanguageState] = useState(() => {
    const stored = localStorage.getItem('justifi-language')
    return LANGUAGES.includes(stored) ? stored : 'English'
  })
  const [darkTheme, setDarkThemeState] = useState(() => localStorage.getItem('justifi-theme') === 'dark')
  const [health, setHealth] = useState(null)
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [jurisdiction, setJurisdiction] = useState('')
  const [legalTimeframe, setLegalTimeframe] = useState('')
  const [initialQuestion, setInitialQuestion] = useState('')
  const t = useCallback((key) => COPY[language][key] || COPY.English[key] || key, [language])

  const setPage = useCallback((nextPage) => {
    if (nextPage !== 'assistant') setInitialQuestion('')
    setPageState(nextPage)
    window.history.replaceState(null, '', `#${nextPage}`)
  }, [])

  function setLanguage(nextLanguage) {
    if (!LANGUAGES.includes(nextLanguage)) return
    setLanguageState(nextLanguage)
    localStorage.setItem('justifi-language', nextLanguage)
  }

  function setDarkTheme(enabled) {
    setDarkThemeState(enabled)
    localStorage.setItem('justifi-theme', enabled ? 'dark' : 'light')
  }

  useEffect(() => {
    document.documentElement.dataset.theme = darkTheme ? 'dark' : 'light'
  }, [darkTheme])

  useEffect(() => {
    let active = true
    requestJson('/api/health')
      .then((health) => {
        if (active) setHealth(health)
      })
      .catch(async () => {
        try {
          const response = await fetch('/api/health')
          const error = await response.json()
          if (active) {
            setHealth({
              services: error?.detail?.services || { sqlite: 'unavailable', ai: 'unavailable' },
              limits: error?.detail?.limits,
            })
          }
        } catch {
          if (active) {
            setHealth({ services: { sqlite: 'unavailable', ai: 'unavailable' } })
          }
        }
      })
    return () => { active = false }
  }, [])

  function startNewChat() {
    const session = { id: crypto.randomUUID(), title: t('newChat'), messages: [], updatedAt: Date.now() }
    setSessions((previous) => [session, ...previous])
    setActiveSessionId(session.id)
    setInitialQuestion('')
    setPage('assistant')
  }

  function explainSource(source) {
    setJurisdiction(source.jurisdiction || '')
    setLegalTimeframe(source.effective_date || '')
    setInitialQuestion(
      `Please explain this legal passage in simple language.\n\n${(
        source.content || source.title || ''
      ).slice(0, 1200)}`,
    )
    setPage('assistant')
  }

  return (
    <div className="application-shell">
      <Sidebar page={page} setPage={setPage} language={language} setLanguage={setLanguage} t={t} onNewChat={startNewChat} onOpenPrivacy={() => setPage('privacy')} />
      <div className="application-main">
        <header className="app-topbar">
          <div className="breadcrumbs"><span>JustiFi</span><span>/</span><strong>{t(({ home: 'navHome', assistant: 'navAssistant', document: 'navDocument', explore: 'navExplore', sources: 'navSources', privacy: 'navPrivacy', settings: 'navSettings' })[page] || 'navHome')}</strong></div>
          <div className="topbar-actions"><ServiceBadge status={health?.services} t={t} /><label className="top-language"><span className="sr-only">{t('preferredLanguage')}</span><select value={language} onChange={(event) => setLanguage(event.target.value)}>{LANGUAGES.map((item) => <option key={item}>{item}</option>)}</select></label></div>
        </header>
        <main className="page-content">
          {page === 'home' && <Dashboard t={t} serviceStatus={health?.services} sessions={sessions} setPage={setPage} setActiveSessionId={setActiveSessionId} />}
          {page === 'assistant' && <AssistantPage key={initialQuestion || activeSessionId || 'assistant'} language={language} t={t} sessions={sessions} setSessions={setSessions} activeSessionId={activeSessionId} setActiveSessionId={setActiveSessionId} jurisdiction={jurisdiction} setJurisdiction={setJurisdiction} legalTimeframe={legalTimeframe} setLegalTimeframe={setLegalTimeframe} initialQuestion={initialQuestion} clearInitialQuestion={setInitialQuestion} onExplainSource={explainSource} />}
          {page === 'document' && <DocumentPage language={language} t={t} onExplainSource={explainSource} maxUploadBytes={health?.limits?.max_upload_bytes || DEFAULT_MAX_FILE_BYTES} />}
          {(page === 'explore' || page === 'sources') && <SourceExplorer page={page} t={t} onExplainSource={explainSource} />}
          {page === 'privacy' && <PrivacyPage t={t} />}
          {page === 'settings' && <SettingsPage language={language} setLanguage={setLanguage} darkTheme={darkTheme} setDarkTheme={setDarkTheme} t={t} setSessions={setSessions} setActiveSessionId={setActiveSessionId} />}
          <footer className="app-footer"><span>JustiFi · Legal information assistant</span><span>{t('disclaimer')}</span></footer>
        </main>
      </div>
    </div>
  )
}

export default App
