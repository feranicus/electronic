// locales/fr.js — Français — register: vous. Translate aggressively: 'conformité', never 'compliance'.
//
// `keyed` maps dotted keys (see locales/en.js). `byEn` maps the English sentence to its translation.
// Anything missing falls back to English, so this file is safe to fill in incrementally.
// NEVER translate the instrument names: NIS2, CRA / Cyber Resilience Act, DORA, EU AI Act, GDPR is
// the exception (RGPD / RODO). Product nouns stay English where the national security press keeps
// them English. Cite the NATIONAL transposition, not the Directive article, in customer-facing copy.
//
// Typography: French spacing is baked in as \u00a0 (nbsp) before : ; ! ? and inside « guillemets ».
// Fragments that concatenate with an inline <span> carry their leading/trailing space on purpose —
// e.g. "Ce que vous ne voyez pas est " + "déjà public". Never trim them.
// tab.* labels are capped at 8 characters: six of them share one 360px phone row.

export const keyed = {
  "assess.refusedH": "Non évalué — il s'agit d'une zone partagée, pas d'une seule entreprise",
  "assess.zoneSurveyGo": "Analyser quand même toute la zone",
  "assess.docLangNote": "Les documents sont rédigés dans la langue sélectionnée ci-dessus. La langue de votre interface n'en fait pas partie : l'anglais est utilisé par défaut.",
  "login.h1a": "Ventes & pre-sales,",
  "login.h1b": "en autonomie.",
  "login.lede": "Un nom en entr\u00e9e, une analyse compl\u00e8te de la surface d'attaque en sortie. Le m\u00eame moteur que derri\u00e8re les bots Telegram \u2014 d\u00e9sormais sur le web, pour chaque commercial.",
  "login.prog1": "Connexion",
  "login.prog2": "V\u00e9rification",
  // ---- qui nous sommes / exp\u00e9rience (added 7 Aug 2026) -----------------------------------
  "nav.about": "Qui nous sommes",
  "tab.about": "\u00c0 propos",
  "exp.h1": "Qui nous sommes",
  "exp.sub": "Quatre immatriculations, deux continents, un interlocuteur responsable \u2014 et les r\u00e9alisations qui les attestent.",
  "exp.lead": "Les acheteurs ont raison de demander qui se trouve derri\u00e8re un produit de s\u00e9curit\u00e9 avant de le laisser approcher leur syst\u00e8me d'information. Voici donc la r\u00e9ponse compl\u00e8te\u00a0: les entit\u00e9s juridiques avec lesquelles vous contractez, leurs num\u00e9ros d'immatriculation et les missions r\u00e9ellement livr\u00e9es. Rien d'offshore, rien de vague.",
  "imp.ctl": "Entit\u00e9 contractante et responsable du traitement",
  "grp.h": "Le groupe",
  "grp.p": "Un seul architecte principal sur quatre juridictions \u2014 un c\u0153ur op\u00e9rationnel europ\u00e9en et une entit\u00e9 am\u00e9ricaine. Nous pouvons facturer depuis l'Estonie, l'Allemagne ou le Portugal, selon ce que pr\u00e9f\u00e8re votre service achats. Facturation en EUR et en USD.",
  "grp.note": "Les num\u00e9ros d'immatriculation sont publics et v\u00e9rifiables au registre du commerce de chaque juridiction. Les donn\u00e9es restent dans l'UE par conception.",
  "grp.jEe": "Estonie",
  "grp.jDe": "Allemagne",
  "grp.jPt": "Portugal",
  "grp.jUs": "Delaware, \u00c9tats-Unis",
  "grp.roleEe": "Si\u00e8ge UE \u00b7 conseil \u00b7 entit\u00e9 contractante",
  "grp.roleDe": "D\u00e9veloppement logiciel commercial",
  "grp.rolePt": "Op\u00e9rations Ib\u00e9rie",
  "grp.roleUs": "R\u00e9alisation cyber & cloud \u00b7 pr\u00e9sence aux \u00c9tats-Unis",
  "exp.who": "L'architecte responsable",
  "exp.role": "Fondateur & architecte principal",
  "exp.whoP": "Vingt-cinq ans dans trois domaines qui ne se rencontrent presque jamais chez une m\u00eame personne\u00a0: l'ing\u00e9nierie du renseignement offensif, le cloud \u00e0 tr\u00e8s grande \u00e9chelle et les r\u00e9seaux d'op\u00e9rateur. C'est cette intersection qui explique la teneur de l'analyse \u2014 elle est r\u00e9dig\u00e9e par quelqu'un qui a construit l'outillage de l'attaquant, le cloud sur lequel il s'ex\u00e9cute et le backbone qu'il traverse.",
  "exp.t1": "Renseignement & cyber",
  "exp.t2": "Cloud, plateforme & donn\u00e9es",
  "exp.t3": "Op\u00e9rateur & r\u00e9seau",
  "exp.work": "Livr\u00e9, en production",
  "exp.workP": "Des clients nomm\u00e9s, \u00e0 l'\u00e9chelle r\u00e9elle \u2014 op\u00e9rateurs, banques, automobile, d\u00e9fense, aviation, \u00e9nergie et assurance.",
  "exp.workNote": "Les chiffres sont ceux publi\u00e9s dans le dossier de comp\u00e9tences de l'architecte. D'autres missions incluent Orange, Sonangol, Cargill et un fabricant de semi-conducteurs.",
  "exp.sTelco": "T\u00e9l\u00e9communications",
  "exp.sAuto": "Automobile",
  "exp.sBank": "Banque",
  "exp.sCarrier": "Op\u00e9rateur Tier\u20111",
  "exp.sAvia": "Aviation",
  "exp.sDef": "D\u00e9fense",
  "exp.sEnergy": "\u00c9nergie",
  "exp.sIns": "Assurance",
  "exp.wTelefonica": "Programme de 200 M\u20ac \u00b7 plus de 400 applications vers AWS \u00b7 d'Oracle \u00e0 PostgreSQL",
  "exp.wDt": "Base de donn\u00e9es de 50 millions d'abonn\u00e9s \u00b7 26 d\u00e9ploiements Red Hat / OpenStack",
  "exp.wVw": "Appliance edge mondiale \u00b7 Kubernetes \u00b7 diagnostic SD-WAN",
  "exp.wBank": "Durcissement des terminaux sur 70 000 postes \u00b7 mise en conformit\u00e9 DORA",
  "exp.wCogent": "Des centaines de projets SD-WAN, MPLS, centre de donn\u00e9es et DDoS",
  "exp.wLuxair": "Deux centres de donn\u00e9es vers Azure \u00b7 migration mainframe et ERP",
  "exp.wElta": "De Cisco / VMware / NetApp vers Canonical OpenStack",
  "exp.wEon": "25 000 terminaux \u00b7 services d'annuaire \u00b7 s\u00e9curit\u00e9 des terminaux",
  "exp.wAon": "Migration RGPD post-Brexit vers un centre de donn\u00e9es de Francfort",
  "exp.build": "Et c'est construit, pas seulement sp\u00e9cifi\u00e9",
  "exp.buildP": "Les architectes capables de concevoir et de livrer sont rares. La preuve de concept est \u00e9crite par l'architecte lui-m\u00eame \u2014 huit langages en production depuis 2001, jusqu'au natif Android.",
  "exp.oss": "Open source\u00a0:",
  "exp.talk": "Parlez \u00e0 l'architecte, pas \u00e0 un commercial",
  "exp.talkP": "Si ce n'est pas utile, cela s'arr\u00eate au bout de vingt minutes. Nous vendons par l'interm\u00e9diaire de revendeurs et d'int\u00e9grateurs\u00a0: la premi\u00e8re conversation ne vous co\u00fbte rien.",

  "nav.why": "Pourquoi c'est décisif",
  "nav.live": "Voir en direct",
  "nav.machine": "La machine",
  "nav.deep": "En détail",
  "nav.secure": "Sécurité",
  "nav.demo": "Démo",
  "nav.contact": "Contact",
  "nav.open": "Ouvrir l'application",
  "nav.login": "Se connecter",
  "nav.home": "Accueil",
  "nav.back": "Retour à la page d'accueil",
  "tab.why": "Enjeux",
  "tab.live": "Live",
  "tab.machine": "Machine",
  "tab.deep": "Détails",
  "tab.secure": "Sûreté",
  "tab.open": "Ouvrir",
  "hero.kick": "Cybergod LLC / S4Biz Group - évaluation du cyber-risque externe et de la conformité UE",
  "hero.h1a": "Saisissez un nom d'entreprise.",
  "hero.h1b": "Quatre dossiers pour le conseil.",
  "hero.h1c": "Deux minutes.",
  "hero.sub": "Toute organisation possède une surface exposée sur Internet qu'elle ne maîtrise jamais entièrement. À partir d'un seul nom d'entreprise, la plateforme cartographie la vôtre à partir de sources publiques uniquement, chiffre le risque en euros, nomme les groupes les plus susceptibles de vous viser et indique quelles échéances européennes s'appliquent déjà - sans toucher un seul de vos systèmes.",
  "hero.cta1": "Ouvrir l'application / Se connecter",
  "hero.cta2": "Voir un rapport de démonstration complet",
  "creed.kick": "Le nom n'est pas un hasard",
  "creed.l1": "Cassandre avait prédit la chute de Troie — et personne ne l'a crue.",
  "creed.l2a": "Nous prédisons les ",
  "creed.l2b": "cyber-risques critiques",
  "creed.l2c": ", nous les arrêtons ",
  "creed.l2d": "avant qu'ils ne se matérialisent",
  "creed.l2e": ", et nous tenons tout ",
  "creed.l2f": "cheval de Troie",
  "creed.l2g": " à l'écart de votre système d'information.",
  "demo.warnH": "CECI EST UNE DÉMONSTRATION — TOUS LES RÉSULTATS SONT FICTIFS",
  "demo.warn1a": "Trojan Empire est une entreprise fictive.",
  "demo.warn1b": " Chaque hôte, certificat, CVE, acteur malveillant et montant en euros ci-dessous est ",
  "demo.warn1c": "inventé",
  "demo.warn1d": " afin de vous montrer la forme du livrable. Rien n'a été scanné. Aucune organisation réelle n'est décrite. Les adresses IP proviennent des plages de documentation de l'IETF (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24), qui ne peuvent atteindre aucune machine réelle.",
  "demo.warn2": "Ce qui n'est pas fictif, c'est la mécanique\u00a0: ces fichiers sortent du même moteur et des mêmes générateurs de présentations qu'une mission facturée.",
  "demo.whatH": "Ce que fait réellement la plateforme",
  "demo.s1h": "Vous saisissez un nom d'entreprise",
  "demo.s1b": "C'est la totalité de la saisie. Aucune plage d'adresses IP, aucun ASN, aucun certificat à coller. Le moteur déduit le reste — y compris les filiales qui opèrent sous des noms totalement différents, là où se cache l'essentiel de l'exposition réelle.",
  "demo.s2h": "Il trouve ce qui est déjà public",
  "demo.s2b": "Entièrement passif. Il lit ce que les scanners d'envergure mondiale, les journaux de transparence des certificats et le DNS public publient déjà sur le parc. Aucun paquet n'est envoyé vers la cible\u00a0: aucune autorisation n'est nécessaire et aucune alarme ne se déclenche.",
  "demo.s3h": "Il prouve ce qui appartient à qui",
  "demo.s3b": "Le plus difficile n'est pas de trouver des hôtes, mais de savoir lesquels sont les leurs. Chaque actif est noté sur la base d'indices indépendants (structure de groupe publiée, certificats, propriétaire enregistré pour chaque IP) et les motifs sont consignés\u00a0: un hôte contesté peut ainsi être expliqué plutôt que débattu.",
  "demo.s4h": "Il rédige les documents du conseil",
  "demo.s4b": "Quatre présentations et un rapport animé\u00a0: ce qui est exposé, ce que cela coûterait en euros, qui viendrait plausiblement s'en prendre à vous et quel service comble chaque écart. Environ trois minutes, de bout en bout.",
  "demo.deckH": "Les livrables — à télécharger",
  "demo.deckLead": "Ce sont les fichiers réels, générés pour l'entreprise fictive Trojan Empire. Ouvrez-les\u00a0: c'est exactement ce qui arrive dans votre boîte de réception pour une cible réelle.",
  "demo.deckWait": "Préparation des livrables de démonstration…",
  "demo.deckErr": "Les livrables de démonstration sont en cours de préparation. Veuillez actualiser la page dans un instant.",
  "demo.d1": "Constats sur la surface d'attaque",
  "demo.d2": "Impact métier, chiffré en euros",
  "demo.d3": "Qui vous viserait, et pourquoi",
  "demo.d4": "Rapport de menace animé",
  "demo.techH": "Comment cela fonctionne, techniquement",
  "demo.accessH": "Lancer l'analyse sur votre propre parc",
  "demo.access1": "La démonstration ci-dessus est ouverte à tous. Les analyses réelles sont réservées aux partenaires agréés\u00a0: chacune consomme de la capacité de scan sous licence et produit un document portant sur une organisation réelle.",
  "demo.access2": "Si vous vendez de la cybersécurité et souhaitez un accès, écrivez-nous\u00a0:",
  "demo.access3": "Merci d'indiquer votre entreprise et votre fonction afin que l'accès puisse être confirmé.",
  "demo.haveAccess": "J'ai déjà un accès",
  "lede.edge": "Votre surface exposée sur Internet s'étend chaque trimestre - un hôte oublié, un portail fournisseur, un VPN que personne n'a jamais désactivé, un certificat qui nomme discrètement un système interne. Un attaquant énumère l'ensemble en quelques minutes, depuis des sources publiques, sans jamais vous toucher. La plupart des organisations ne se sont jamais regardées ainsi.",
  "q3.h": "Trois questions décident d'un budget de sécurité. Vous devriez pouvoir répondre aux trois dès aujourd'hui.",
  "clocks.lede": "Trois textes européens concernent désormais la plupart des organisations de taille intermédiaire\u00a0: NIS2, le Cyber Resilience Act et l'EU AI Act. Ces dates sont inscrites dans la loi, pas sur la diapositive d'un fournisseur - et les sanctions se mesurent au chiffre d'affaires mondial.",
  "touch.body": "Ce n'est ni un test d'intrusion ni un scan de vos systèmes. Aucun port n'est sondé, aucune connexion tentée, aucun agent installé, aucun identifiant requis. Seul est lu ce qui est déjà public - l'équivalent, sur Internet, de noter quelles portes sont visibles depuis la rue.",
  "touch.bold": "C'est précisément pour cela qu'il peut vous montrer ce qu'un attaquant voit déjà\u00a0: sans demande de changement, sans fenêtre de maintenance et sans un seul paquet envoyé vers votre infrastructure.",
  "earn.01h": "Devant le conseil",
  "earn.01b": "Présentez l'exposition et le montant en euros plutôt que des adjectifs.",
  "earn.02h": "Avant un audit",
  "earn.02b": "Applicabilité, obligations et échéances NIS2, CRA et EU AI Act sur une seule page.",
  "earn.03h": "Après une acquisition",
  "earn.03b": "Découvrez le parc dont vous venez d'hériter, cartographié de l'extérieur.",
  "earn.04h": "Risque fournisseurs",
  "earn.04b": "Évaluez un fournisseur de la même manière - sans accès, sans questionnaire, sans attente.",
  "earn.05h": "Trimestre après trimestre",
  "earn.05b": "Relancez l'analyse et voyez exactement ce qui a changé sur votre périmètre.",
  "earn.06h": "Votre premier regard",
  "earn.06b": "La plupart des organisations découvrent quelque chose de public dont elles ignoraient l'existence.",
  "demo.t1h": "L'attribution avant l'analyse.",
  "demo.t1b": " La propriété est notée sur une échelle de confiance de 0 à 100, construite à partir d'indices indépendants — la structure de groupe publiée par l'entreprise elle-même, les noms portés par les certificats, l'organisation enregistrée pour chaque IP, les identifiants de tenant chez les éditeurs, le DNS que l'entreprise contrôle. Deux indices faibles qui concordent l'emportent sur un indice fort isolé, et chaque score conserve les règles qui l'ont produit.",
  "demo.t2h": "La protection contre les colocataires.",
  "demo.t2b": " Un bloc d'adresses partagé n'est pas un client. Lorsque plusieurs entreprises se partagent une plage d'hébergeur, c'est la propriété enregistrée IP par IP qui tranche\u00a0: l'interface d'administration exposée d'un voisin n'apparaît jamais dans votre rapport.",
  "demo.t3h": "L'IA rédige la prose, jamais les faits.",
  "demo.t3b": " La criticité, les preuves et les identifiants CVE proviennent exclusivement des données de scan. Le modèle de langage reformule l'explication et la remédiation, et un second modèle, d'un autre éditeur, en contrôle le résultat de façon indépendante. Toute CVE citée par le modèle mais absente des preuves est supprimée avant la génération des présentations.",
  "demo.t4h": "Un rendu déterministe.",
  "demo.t4b": " Les présentations sont générées par du code, non par un modèle\u00a0: la même entrée produit toujours le même document — et la mise en page est vérifiée automatiquement contre les débordements avant toute livraison.",
  "demo.t5h": "Hébergé dans l'UE.",
  "demo.t5b": " L'application, les données et les journaux tournent à Francfort. Les analyses sont passives\u00a0: aucun paquet n'est envoyé vers la cible.",
  "faq.1q": "«\u00a0Est-ce légal\u00a0?\u00a0»",
  "faq.1a": "Oui. La plateforme s'appuie sur des sources publiques que n'importe quel chercheur pourrait consulter et n'interagit jamais avec vos systèmes. Rien n'est exploité, aucune connexion n'est établie.",
  "faq.2q": "«\u00a0Quelle est sa fiabilité\u00a0?\u00a0»",
  "faq.2a": "Chaque constat s'accompagne de la preuve qui le fonde. Lorsqu'une source est inaccessible, il indique «\u00a0inconnu\u00a0» plutôt que d'inventer une faiblesse - et il vous demande de confirmer tout ce qu'il n'a pas pu établir.",
  "faq.3q": "«\u00a0Que devons-nous fournir\u00a0?\u00a0»",
  "faq.3a": "Le nom de votre entreprise. Aucun accès, aucun questionnaire, aucun NDA pour commencer et rien à installer. Les montants en euros sont des fourchettes modélisées, dont les hypothèses sont affichées.",
  "login.h": "Connexion",
  "login.zero": "Accès zero trust pour les équipes commerciales en cybersécurité.",
  "login.email": "E-mail professionnel",
  "login.pw": "Mot de passe d'accès",
  "login.send": "Envoyez-moi un code",
  "login.code": "Code à 6 chiffres",
  "login.verify": "Vérifier",
  "login.sent": "Un code à 6 chiffres a été envoyé dans votre boîte de réception.",
  "login.portal": "Se connecter au portail",
  "login.pwPh": "Mot de passe d'accès partagé",
  "login.continue": "Continuer →",
  "login.codeH": "Saisissez votre code",
  "login.codeSub": "Nous avons envoyé un code à 6 chiffres à ",
  "login.back": "← Retour à la présentation",
  "login.iam": "Identité et accès",
  "login.step1": "Votre identité",
  "login.step1b": "votre e-mail agréé + le mot de passe d'accès partagé",
  "login.step2": "Code à usage unique",
  "login.step2b": "Un code à 6 chiffres arrive dans votre boîte de réception",
  "login.step3": "Vous êtes connecté",
  "login.step3b": "Votre espace personnel\u00a0: analyses, assistant, historique",
  "login.foot": "Zero trust · partenaires agréés uniquement",

  // ================================================================================================
  // L'ESPACE CLIENT (tout ce qui est derrière la connexion).
  // Rien de ce que le SERVEUR rédige n'apparaît ici : phases du moteur, noms de fichiers, questions
  // de clarification et messages d'erreur de l'API arrivent en tant que données et ne sont jamais
  // traduits — une entrée manquante afficherait une clé brute à la place d'une sortie serveur.
  // ================================================================================================

  // ---- barre latérale / barre d'onglets sur téléphone -------------------------------------------
  // COURT par contrat : les quatre premiers libellés occupent le rail étroit du bureau ET la barre
  // d'onglets du téléphone. Au-delà de ~11 caractères le libellé passe à la ligne et la barre double
  // de hauteur. « Analyse / Conformité / Assistant / Historique » reprend le vocabulaire du site.
  "side.assess": "Analyse",
  "side.compliance": "Conformité",
  "side.assistant": "Assistant",
  "side.history": "Historique",
  "side.logout": "Déconnexion",
  "side.signedIn": "connecté en tant que",
  // Les trois liens légaux portent en anglais le nom allemand des pages (§5 TMG / DSGVO). En
  // français on garde la dénomination usuelle du site vitrine (voir byEn plus bas) : le pied de
  // page et la barre latérale doivent nommer la même page de la même façon.
  "side.impressum": "Mentions légales",
  "side.privacy": "Protection des données",
  "side.contact": "Contact",

  // ---- Analyse (nouvelle analyse) ---------------------------------------------------------------
  "assess.h1": "Nouvelle analyse",
  "assess.sub": "Une seule saisie : un nom d'entreprise ou un domaine. Le moteur détermine toute la surface exposée, balaie Shodan et rédige les quatre présentations pour le conseil. Aucune adresse IP, aucun ASN, aucun certificat à saisir.",
  "assess.company": "Nom de l'entreprise",
  "assess.companyPh": "ex. Volkswagen AG",
  "assess.docLang": "Langue du document",
  "assess.go": "Analyser",
  "assess.running": "Analyse en cours…",
  "assess.phaseIdle": "Traitement en cours…",
  "assess.phaseStart": "Démarrage du moteur…",
  "assess.phaseRescope": "Redéfinition du périmètre avec vos réponses…",
  "assess.noteLong": "Traitement toujours en cours. Une exécution longue signifie généralement que la reconnaissance Shodan a trouvé un parc étendu, ou qu'un modèle d'IA est lent et que nous basculons vers le suivant — le journal ci-dessus indique lequel.",
  "assess.noteShort": "En général 3 à 7 minutes : la reconnaissance Shodan est la partie longue (~2 à 3 min), puis l'IA rédige le texte (~1 min).",
  "assess.noteKeepOpen": "Gardez cet onglet ouvert ; actualiser la page annule l'exécution.",
  "assess.logStarting": "Démarrage…",
  "assess.statusWorking": "Traitement en cours — cela prend généralement environ deux minutes.",
  "assess.done": "Terminé. Vos quatre présentations sont prêtes.",
  "assess.download": "Télécharger",
  // Bannières de connexion en flux. assess.dropped est aussi comparée dans es.onopen pour effacer
  // la bannière : elle doit rester UNE seule clé (ne pas la scinder).
  "assess.reconnected": "Reconnecté à une analyse déjà en cours sur le serveur.",
  "assess.dropped": "Connexion interrompue — reconnexion… (l'analyse se poursuit sur le serveur)",
  // Repli utilisé uniquement lorsque le serveur n'envoie aucun message.
  "assess.errFailed": "L'analyse a échoué.",
  "assess.errStart": "Impossible de démarrer l'analyse.",
  "assess.errRefine": "Impossible d'affiner l'analyse.",
  // panneau de clarification / affinage après l'exécution
  "assess.refineH": "Affiner cette analyse",
  "assess.refineSub": "Les présentations ci-dessus sont prêtes. Pour préciser le périmètre, répondez ci-dessous à ce qui vous concerne : confirmez ce qui vous appartient, ajoutez les plages d'adresses IP ou les systèmes que la reconnaissance automatique n'a pas pu voir, ou signalez ce qui n'est pas à vous. Je redéfinirai le périmètre et régénérerai les quatre présentations ainsi que le rapport animé.",
  "assess.yes": "Oui",
  "assess.refineGo": "Affiner et régénérer",
  "assess.refineBusy": "Affinage en cours…",
  "assess.refineHint": "Répondez à au moins une question pour affiner.",

  // ---- Conformité (NIS2 / CRA / EU AI Act) ------------------------------------------------------
  "comp.h1": "Évaluation de conformité",
  // Quatre fragments de liaison autour des trois titres réglementaires en gras, jamais traduits.
  // L'assemblage est : a + NIS2 + b + Cyber Resilience Act + c + EU AI Act + d. Les prépositions
  // françaises (« à », « au », « à l' ») portent donc sur le fragment qui PRÉCÈDE chaque nom, et
  // comp.sub.c se termine par une élision — pas d'espace finale après « l' ».
  "comp.sub.a": "Une seule saisie : un nom d'entreprise. Le moteur évalue l'exposition à ",
  "comp.sub.b": ", au ",
  "comp.sub.c": " et à l'",
  "comp.sub.d": " — applicabilité, obligations, écarts, échéances et exposition aux sanctions — et rédige trois présentations par régime, une feuille de route et un rapport animé. Il déduit le périmètre à partir du nom ; vous le confirmez ensuite.",
  "comp.company": "Nom de l'entreprise",
  "comp.companyPh": "ex. Siemens Healthineers AG",
  "comp.docLang": "Langue du document",
  "comp.go": "Évaluer la conformité",
  "comp.running": "Évaluation en cours…",
  "comp.phaseIdle": "Traitement en cours…",
  "comp.phaseStart": "Démarrage du moteur…",
  "comp.phaseRescope": "Redéfinition du périmètre avec vos réponses…",
  "comp.note": "En général une minute environ. Gardez cet onglet ouvert ; actualiser la page annule l'exécution.",
  "comp.logStarting": "Démarrage…",
  "comp.done": "Terminé. Vos présentations NIS2, CRA, AI Act et feuille de route sont prêtes.",
  "comp.download": "Télécharger",
  "comp.openReport": "Ouvrir le rapport",
  "comp.reconnected": "Reconnecté à une évaluation de conformité déjà en cours.",
  "comp.dropped": "Connexion interrompue — reconnexion… (l'évaluation se poursuit sur le serveur)",
  "comp.errFailed": "L'évaluation a échoué.",
  "comp.errStart": "Impossible de démarrer l'évaluation.",
  "comp.errRefine": "Impossible d'affiner l'évaluation.",
  "comp.confirmH": "Confirmez le périmètre",
  "comp.confirmSub": "Les présentations ci-dessus reposent sur des hypothèses déduites du nom de l'entreprise. La conformité dépend de faits que je ne peux que supposer : confirmez ceux ci-dessous et je redéfinirai le périmètre et régénérerai les documents.",
  "comp.yes": "Oui",
  "comp.refineGo": "Affiner et régénérer",
  "comp.refineBusy": "Affinage en cours…",
  "comp.refineHint": "Répondez à au moins une question pour affiner.",

  // ---- Assistant (Cassandra) ---------------------------------------------------------------------
  "assist.h1": "Assistant",
  "assist.sub": "Cassandra - recherche, qualification MEDDPICC et rédaction de messages de prospection pour vos comptes.",
  "assist.greeting": "Bonjour, je suis Cassandra - votre copilote avant-vente. Demandez-moi une recherche sur une entreprise, une analyse MEDDPICC ou un texte de prospection.",
  "assist.ph": "Posez votre question à Cassandra…",
  "assist.send": "Envoyer",
  "assist.errServer": "Une erreur est survenue. Réessayez.",
  "assist.errNet": "Impossible de joindre le serveur. Réessayez.",

  // ---- Historique --------------------------------------------------------------------------------
  "hist.h1": "Historique",
  "hist.sub": "Toutes les analyses que vous avez lancées, avec les présentations prêtes à être retéléchargées.",
  "hist.loading": "Chargement…",
  "hist.err": "Impossible de charger l'historique.",
  // « Nouvelle analyse » doit reprendre mot pour mot assess.h1 : c'est le nom de l'écran visé.
  "hist.empty": "Aucune analyse pour l'instant. Lancez-en une depuis « Nouvelle analyse ».",
};

export const byEn = {
  " blocks accidental commits.":
    " empêche les commits accidentels.",
  " internet footprint itself, then hunts every exposure, prices it, and writes the decks.":
    " la surface exposée de la cible, puis traque chaque exposition, la chiffre et rédige les présentations.",
  "+ a one-time code emailed to that inbox":
    "+ un code à usage unique envoyé à cette boîte",
  ". Guessing the first two isn't enough.":
    ". Deviner les deux premiers ne suffit pas.",
  "1 - One input: a company name. From Telegram, or from the cybergod.ai web app.":
    "1 - Une seule saisie\u00a0: un nom d'entreprise. Depuis Telegram ou depuis l'application web cybergod.ai.",
  "10 - patchwatch backs up to Spaces, then patches the server itself every 3 days.":
    "10 - patchwatch sauvegarde vers Spaces, puis met à jour le serveur lui-même tous les 3 jours.",
  "11 - One command builds, scans and ships it - and proves the container really holds the new code.":
    "11 - Une seule commande compile, analyse et déploie - et prouve que le conteneur contient réellement le nouveau code.",
  "11 live security rules: brute force, spraying, scanners, IDOR probes, exfil bursts":
    "11 règles de sécurité en direct\u00a0: force brute, password spraying, scanners, sondes IDOR, pics d'exfiltration",
  "2 - Zero-trust: approved email + password + a one-time code emailed to that inbox.":
    "2 - Zero trust\u00a0: e-mail agréé + mot de passe + un code à usage unique envoyé à cette boîte.",
  "2 CRIT / 4 HIGH / evidence + fixes":
    "2 CRIT / 4 ÉLEVÉ / preuves + correctifs",
  "2FA code / HTTPS":
    "Code 2FA / HTTPS",
  "2nd model checks it":
    "un 2e modèle le vérifie",
  "3 - The engine auto-resolves the company's entire footprint. You type no IPs.":
    "3 - Le moteur détermine seul toute la surface exposée de l'entreprise. Vous ne saisissez aucune adresse IP.",
  "30+ super-filters; edge appliances (firewalls, VPN concentrators) = CRITICAL":
    "Plus de 30 super-filtres\u00a0; équipements de périmètre (pare-feu, concentrateurs VPN) = CRITIQUE",
  "4 - It sweeps Shodan for every exposed door - and pivots on their own private CA.":
    "4 - Il balaie Shodan à la recherche de chaque porte exposée - et pivote sur leur propre autorité de certification privée.",
  "4 decks":
    "4 présentations",
  "4 decks + live report":
    "4 présentations + rapport animé",
  "5 - A multi-vendor AI chain writes the prose; templates lock the numbers into the decks.":
    "5 - Une chaîne d'IA multi-éditeurs rédige le texte\u00a0; les gabarits verrouillent les chiffres dans les présentations.",
  "6 - A SECOND AI, from a different vendor, audits the findings for false positives before you ever see them.":
    "6 - Une SECONDE IA, issue d'un autre éditeur, audite les constats à la recherche de faux positifs avant que vous ne les voyiez.",
  "7 - Decks land first - then it asks what it could not resolve. You answer, it re-scopes and rebuilds.":
    "7 - Les présentations arrivent d'abord - puis il vous demande ce qu'il n'a pas pu établir. Vous répondez, il redéfinit le périmètre et régénère tout.",
  "8 - Compliance: NIS2, the Cyber Resilience Act and the EU AI Act - from the same one input.":
    "8 - Conformité\u00a0: NIS2, le Cyber Resilience Act et l'EU AI Act - à partir de la même unique saisie.",
  "9 - Every login, assessment, audit and patch is logged live to Grafana.":
    "9 - Chaque connexion, analyse, audit et mise à jour est journalisé en direct dans Grafana.",
  "<code>audit_fp.py</code> picks an auditor that differs from the deck author - it refuses to self-audit":
    "<code>audit_fp.py</code> choisit un auditeur différent de l'auteur des présentations - il refuse de s'auditer lui-même",
  "<code>patchwatch/</code> systemd timer; backup-first (abort if the backup fails)":
    "Minuteur systemd <code>patchwatch/</code>\u00a0; sauvegarde d'abord (abandon si la sauvegarde échoue)",
  "<code>pptxgenjs</code> templates lock layout; numbers stay deterministic":
    "Les gabarits <code>pptxgenjs</code> verrouillent la mise en page\u00a0; les chiffres restent déterministes",
  "<code>python ship.py</code>: test to commit to push to deploy to VERIFY":
    "<code>python ship.py</code>\u00a0: test puis commit puis push puis déploiement puis VÉRIFICATION",
  "<code>python-telegram-bot</code>, one per bot, in Docker":
    "<code>python-telegram-bot</code>, un par bot, dans Docker",
  "A chain of AI models writes the words; fixed templates guarantee the structure and the maths. You get <b>Findings / C-BIQ (EUR) / GEOPOL / DELTAS</b> plus a <b>live animated report</b> you present on screen.":
    "Une chaîne de modèles d'IA rédige le texte\u00a0; des gabarits figés garantissent la structure et les calculs. Vous obtenez <b>Findings / C-BIQ (EUR) / GEOPOL / DELTAS</b> ainsi qu'un <b>rapport animé en direct</b> que vous présentez à l'écran.",
  "A findings spreadsheet with no price attached to anything":
    "Un tableur de constats où rien n'est chiffré",
  "A number the board can actually make a decision on":
    "Un chiffre sur lequel le conseil peut réellement décider",
  "A real approved email address + the shared password ":
    "Une adresse e-mail agréée réelle + le mot de passe partagé ",
  "A second AI audits the first":
    "Une seconde IA audite la première",
  "A server nobody patches gets hacked. Every 3 days it <b>backs itself up</b> to Spaces, upgrades the OS/Docker, and an AI writes a risk digest. Reboots happen at 4am.":
    "Un serveur que personne ne met à jour finit compromis. Tous les 3 jours, il <b>se sauvegarde</b> vers Spaces, met à jour l'OS et Docker, et une IA rédige une synthèse des risques. Les redémarrages ont lieu à 4 h du matin.",
  "AI AUDIT":
    "AUDIT IA",
  "AI MODELS":
    "MODÈLES IA",
  "AI digest to Telegram + Grafana":
    "Synthèse IA vers Telegram + Grafana",
  "APT41/Winnti +4 adversaries":
    "APT41/Winnti + 4 adversaires",
  "ASNs+prefixes from RIPE + CAIDA + PeeringDB + bgpview":
    "ASN et préfixes depuis RIPE + CAIDA + PeeringDB + bgpview",
  "Always watching":
    "Sous surveillance permanente",
  "An annual test, scoped to what you remembered to list":
    "Un test annuel, limité à ce que vous avez pensé à déclarer",
  "An isolated container stack; existing services and the firewall are untouched.":
    "Une pile de conteneurs isolée\u00a0; les services existants et le pare-feu restent intacts.",
  "Assessing Volkswagen AG ...":
    "Analyse de Volkswagen AG ...",
  "Because you asserted the fact, the zero-false-positive rules stay intact":
    "Parce que c'est vous qui affirmez le fait, les règles zéro faux positif restent intactes",
  "Before you ever see the decks, a <b>different model from a different vendor</b> re-reads every finding and challenges anything that looks like it isn't really theirs. A model is never allowed to mark its own homework.":
    "Avant même que vous ne voyiez les présentations, un <b>modèle différent, issu d'un autre éditeur</b>, relit chaque constat et conteste tout ce qui ne semble pas réellement appartenir à l'entreprise. Aucun modèle n'est autorisé à corriger sa propre copie.",
  "Betrieben in Deutschland &middot; Server in Frankfurt am Main (FRA1) &middot; Ihre Daten bleiben in der EU.":
    "Exploité en Allemagne &middot; serveurs à Francfort-sur-le-Main (FRA1) &middot; vos données restent dans l'UE.",
  "Brains":
    "Intelligence",
  "Brand domains/subdomains: <code>crt.sh</code> + CertSpotter CT logs + DNS probe":
    "Domaines et sous-domaines de la marque\u00a0: journaux CT <code>crt.sh</code> + CertSpotter + sondage DNS",
  "CDN/honeypot false-positives dropped automatically":
    "Faux positifs CDN et pots de miel écartés automatiquement",
  "CLARIFY":
    "CLARIFICATION",
  "COMPLIANCE":
    "CONFORMITÉ",
  "Change the code, run one thing, it's live - and it <b>proves</b> the running container actually holds the new code before it reports success.":
    "Modifiez le code, lancez une seule commande, c'est en ligne - et il <b>prouve</b> que le conteneur en service contient bien le nouveau code avant d'annoncer la réussite.",
  "Code emailed. Reply /verify <code> (valid 10 min).":
    "Code envoyé par e-mail. Répondez /verify <code> (valable 10 min).",
  "Compliance deadlines live in somebody&rsquo;s inbox.":
    "Les échéances de conformité dorment dans la boîte mail de quelqu&rsquo;un.",
  "Compliance: NIS2, CRA, EU AI Act":
    "Conformité\u00a0: NIS2, CRA, EU AI Act",
  "Cyber Resilience Act":
    "Cyber Resilience Act",
  "Cybergod LLC / S4Biz Group - external cyber-risk and EU compliance assessment / one company name in, four boardroom documents out.":
    "Cybergod LLC / S4Biz Group - évaluation du cyber-risque externe et de la conformité UE / un nom d'entreprise en entrée, quatre documents de conseil en sortie.",
  "DELIVERABLES":
    "LIVRABLES",
  "DO Spaces tarball + optional droplet snapshot":
    "Archive tar vers DO Spaces + instantané du droplet en option",
  "Datenschutz / Privacy":
    "Protection des données",
  "Deep ":
    "Analyse ",
  "DeepSeek prose":
    "Texte rédigé par DeepSeek",
  "Deterministic fallback holds the fixed facts, so obligations and fines are right even if the model is down":
    "Un repli déterministe conserve les faits fixes\u00a0: obligations et sanctions restent exactes même si le modèle est indisponible",
  "Do this in the web app":
    "À faire dans l'application web",
  "Done in 2m 10s. 4 decks ready.":
    "Terminé en 2 min 10 s. 4 présentations prêtes.",
  "ENGINE":
    "MOTEUR",
  "EU AI Act":
    "EU AI Act",
  "Engine-hash check: sha256 inside the container vs the repo - a stale container fails the ship":
    "Contrôle d'empreinte du moteur\u00a0: sha256 dans le conteneur comparé au dépôt - un conteneur obsolète fait échouer la livraison",
  "Every audit is logged: auditor vs author, verdict, dropped, refused":
    "Chaque audit est journalisé\u00a0: auditeur contre auteur, verdict, constats écartés, refus",
  "Every exposure modelled in euros, with the method shown":
    "Chaque exposition modélisée en euros, avec la méthode affichée",
  "Every finding carries the evidence behind it. Where a source cannot be reached it says “unknown” rather than inventing a weakness - and it asks you to confirm anything it could not resolve.":
    "Chaque constat s'accompagne de la preuve qui le fonde. Lorsqu'une source est inaccessible, il indique «\u00a0inconnu\u00a0» plutôt que d'inventer une faiblesse - et il vous demande de confirmer tout ce qu'il n'a pas pu établir.",
  "Every login, assessment, audit, cost and patch prints a structured line that flows into <b>your existing Grafana</b> - no second monitoring stack.":
    "Chaque connexion, analyse, audit, coût et mise à jour écrit une ligne structurée qui alimente <b>votre Grafana existant</b> - aucune seconde pile de supervision.",
  "FOOTPRINT":
    "SURFACE EXPOSÉE",
  "Fair questions":
    "Questions légitimes",
  "For boards, CISOs and risk owners":
    "Pour les conseils d'administration, les RSSI et les responsables des risques",
  "From just the name the engine finds the company's <b>networks, domains and certificates</b> - then hunts, scores and writes. You never hand it an IP.":
    "À partir du seul nom, le moteur trouve les <b>réseaux, domaines et certificats</b> de l'entreprise - puis il traque, évalue et rédige. Vous ne lui fournissez jamais d'adresse IP.",
  "GITHUB CI/CD":
    "CI/CD GITHUB",
  "GMAIL API":
    "API GMAIL",
  "GRAFANA":
    "GRAFANA",
  "Grounded ONLY in a committed reference of the primary legal texts":
    "Fondé UNIQUEMENT sur une référence versionnée des textes juridiques d'origine",
  "Guided tour":
    "Visite guidée",
  "Hallucination guard: any CVE not in the scan evidence is stripped, and logged":
    "Garde-fou anti-hallucination\u00a0: toute CVE absente des preuves de scan est supprimée et journalisée",
  "Hard guardrail: it can never empty a deck, or drop more than 40% of findings":
    "Garde-fou strict\u00a0: il ne peut jamais vider une présentation ni écarter plus de 40 % des constats",
  "Hover a box to see its wires. Click it to jump to the details. Or hit play for a guided tour.":
    "Survolez un bloc pour voir ses liaisons. Cliquez dessus pour accéder au détail. Ou lancez la visite guidée.",
  "How it usually goes":
    "Comment cela se passe d'ordinaire",
  "Impressum":
    "Mentions légales",
  "It asks you what it couldn't work out":
    "Il vous demande ce qu'il n'a pas pu établir",
  "It is whether you know what.":
    "Mais de savoir quoi.",
  "It patches itself":
    "Il se met à jour tout seul",
  "It queries Shodan for exposed remote-access, databases, VPNs, mail, industrial gear and known-vulnerable systems - plus the killer pivot: the company's own private CA and whois-org, which reveal the hidden estate.":
    "Il interroge Shodan sur les accès distants, bases de données, VPN, serveurs de messagerie, équipements industriels et systèmes vulnérables connus qui sont exposés - et exploite le pivot décisif\u00a0: l'autorité de certification privée de l'entreprise et son organisation whois, qui révèlent la partie cachée du parc.",
  "Keys live only on the server or as encrypted GitHub secrets; ":
    "Les clés résident uniquement sur le serveur ou sous forme de secrets GitHub chiffrés\u00a0; ",
  "Kontakt / Contact":
    "Contact",
  "LIVE NOW":
    "EN DIRECT",
  "Locked ":
    "Verrouillé ",
  "Minutes, not weeks - and repeatable whenever you want":
    "Des minutes, pas des semaines - et reproductible quand vous le voulez",
  "Multi-VENDOR chain with failover - a 429 is provider-wide, so the backup must be another vendor":
    "Chaîne multi-ÉDITEURS avec bascule - un 429 touche tout le fournisseur, la solution de secours doit donc venir d'un autre éditeur",
  "NIS2 / CRA / AI Act":
    "NIS2 / CRA / AI Act",
  "NIS2 — Germany":
    "NIS2 — Allemagne",
  "Never breaks the neighbours":
    "Ne perturbe jamais les voisins",
  "Nobody walks in":
    "Personne n'entre par hasard",
  "Not legal advice - and every deck says so":
    "Ne constitue pas un conseil juridique - et chaque présentation le rappelle",
  "Nothing of yours is touched":
    "Rien de ce qui vous appartient n'est touché",
  "OTP delivered via <b>Gmail API over HTTPS</b> (droplet blocks SMTP ports)":
    "Code à usage unique transmis via l'<b>API Gmail en HTTPS</b> (le serveur bloque les ports SMTP)",
  "Observability":
    "Observabilité",
  "One gate shared by the bots AND the web app - they can never disagree":
    "Un contrôle d'accès unique partagé par les bots ET l'application web - ils ne peuvent jamais diverger",
  "One input. Zero flags.":
    "Une seule saisie. Aucun paramètre.",
  "Open the app":
    "Ouvrir l'application",
  "Outside services":
    "Services externes",
  "Ownership gate: a discovered domain is a CANDIDATE, never proof":
    "Contrôle de propriété\u00a0: un domaine découvert est un CANDIDAT, jamais une preuve",
  "PATCHWATCH":
    "PATCHWATCH",
  "Paid facets: <code>has_vuln</code>, <code>vuln:CVE</code>, <code>tag:ics</code>, <code>ssl.jarm</code>":
    "Facettes payantes\u00a0: <code>has_vuln</code>, <code>vuln:CVE</code>, <code>tag:ics</code>, <code>ssl.jarm</code>",
  "Per-run cost ledger in SQLite - true lifetime spend, survives log retention":
    "Registre des coûts par exécution en SQLite - dépense cumulée réelle, indépendante de la rétention des journaux",
  "Plain English for everyone; under the hood for the engineer. Click a box in the map above to jump here.":
    "En clair pour tout le monde\u00a0; sous le capot pour les ingénieurs. Cliquez sur un bloc de la carte ci-dessus pour arriver ici.",
  "Questions are DETERMINISTIC, not LLM-written - auditable, free, never invents a domain":
    "Les questions sont DÉTERMINISTES, non rédigées par un LLM - auditables, gratuites, jamais un domaine inventé",
  "React cabinet: Assess / Compliance / Assistant / History":
    "Espace React\u00a0: Analyse / Conformité / Assistant / Historique",
  "Request an assessment":
    "Demander une analyse",
  "SALES":
    "COMMERCIAL",
  "SHODAN":
    "SHODAN",
  "SPACES":
    "SPACES",
  "Safety nets":
    "Filets de sécurité",
  "Scanned before ship":
    "Analysé avant livraison",
  "Scope blow-out guard - it refuses to build decks from an unverified estate":
    "Garde-fou contre l'explosion du périmètre - il refuse de générer des présentations à partir d'un parc non vérifié",
  "Secrets never in git":
    "Jamais de secrets dans git",
  "Secure-by-design, in plain terms.":
    "La sécurité dès la conception, en termes simples.",
  "See it ":
    "Voir en ",
  "Shared auth module: constant-time compare, lockout, 10-min codes":
    "Module d'authentification partagé\u00a0: comparaison à temps constant, verrouillage, codes valables 10 min",
  "Shipping is one command":
    "La livraison tient en une commande",
  "Shodan (paid)":
    "Shodan (payant)",
  "Shodan - what's exposed":
    "Shodan - ce qui est exposé",
  "Stop tour":
    "Arrêter la visite",
  "Swipe the map sideways to explore &rarr;":
    "Faites glisser la carte latéralement pour explorer &rarr;",
  "Tagged safe-points and <code>--rollback</code> to any known-good state":
    "Points de restauration étiquetés et <code>--rollback</code> vers n'importe quel état sain connu",
  "Telegram / one name":
    "Telegram / un seul nom",
  "The AI writes it - you get five artifacts":
    "L'IA rédige - vous recevez cinq livrables",
  "The LLM can FLAG, but a finding is only dropped when deterministic ownership data agrees":
    "Le LLM peut SIGNALER, mais un constat n'est écarté que si les données déterministes de propriété le confirment",
  "The board asks what it would actually cost. Nobody knows.":
    "Le conseil demande ce que cela coûterait réellement. Personne ne le sait.",
  "The chat loops - watch the four .pptx files land.":
    "La conversation tourne en boucle - regardez arriver les quatre fichiers .pptx.",
  "The clocks are ":
    "Les compteurs sont ",
  "The decks land <b>first</b>. Then the engine tells you what it could not resolve - which related domains are yours, your netblocks if you sit behind a CDN, anything in the report that isn't yours - you answer, and it re-scopes and rebuilds.":
    "Les présentations arrivent <b>d'abord</b>. Le moteur vous indique ensuite ce qu'il n'a pas pu établir - quels domaines apparentés vous appartiennent, vos blocs d'adresses si vous êtes derrière un CDN, tout ce qui, dans le rapport, n'est pas à vous - vous répondez, et il redéfinit le périmètre et régénère tout.",
  "The engine + auto-discovery":
    "Le moteur + la découverte automatique",
  "The model infers sector/size/product/AI profile and STATES it - you confirm and it rebuilds":
    "Le modèle déduit le secteur, la taille, les produits et le profil IA, et l'ÉNONCE - vous confirmez et il régénère",
  "The question is not whether something of yours is exposed.":
    "La question n'est pas de savoir si quelque chose vous appartenant est exposé.",
  "The regulatory clock, on one slide.":
    "Le calendrier réglementaire, sur une seule diapositive.",
  "The run is owned by the SERVER - lock your phone, it keeps going":
    "L'exécution appartient au SERVEUR - verrouillez votre téléphone, elle continue",
  "The same one input, pointed at regulation. It grades the company against the three horizontal EU digital laws and writes <b>three regime decks, a roadmap deck and an animated report</b> - applicability, duties, gaps, deadlines and the maximum fine.":
    "La même unique saisie, appliquée à la réglementation. Il évalue l'entreprise au regard des trois textes numériques horizontaux de l'UE et rédige <b>trois présentations par régime, une feuille de route et un rapport animé</b> - applicabilité, obligations, écarts, échéances et sanction maximale.",
  "The whole ":
    "Toute la ",
  "This is the entire product - texting a bot. The chat below plays the real flow: log in, ask, get four decks.":
    "C'est tout le produit - écrire à un bot. La conversation ci-dessous rejoue le déroulement réel\u00a0: se connecter, demander, recevoir quatre présentations.",
  "Trivy (deps+image), CodeQL SAST, ruff, pytest - every change checked before it reaches the server.":
    "Trivy (dépendances et image), CodeQL SAST, ruff, pytest - chaque modification est contrôlée avant d'atteindre le serveur.",
  "Two front doors, one input":
    "Deux portes d'entrée, une seule saisie",
  "Type a company name - in <b>Telegram</b>, or in the <b>cybergod.ai web app</b>. Same engine, same decks. Two bots live on the server: the <b>assessment bot</b> runs the scan, <b>cassandra</b> answers questions about the findings.":
    "Saisissez un nom d'entreprise - dans <b>Telegram</b> ou dans l'<b>application web cybergod.ai</b>. Même moteur, mêmes présentations. Deux bots vivent sur le serveur\u00a0: le <b>bot d'analyse</b> exécute la recherche, <b>cassandra</b> répond aux questions sur les constats.",
  "Under the hood - for the engineer":
    "Sous le capot - pour les ingénieurs",
  "Verified. You're in.":
    "Vérifié. Vous êtes connecté.",
  "WEB APP":
    "APPLICATION WEB",
  "Weeks between the question and the answer":
    "Des semaines entre la question et la réponse",
  "What you cannot see is ":
    "Ce que vous ne voyez pas est ",
  "What you get here":
    "Ce que vous obtenez ici",
  "Where it earns its place":
    "Là où cela prend tout son sens",
  "Yes. It uses public sources any researcher could look up, and never interacts with your systems. Nothing is exploited, nothing is logged into.":
    "Oui. La plateforme s'appuie sur des sources publiques que n'importe quel chercheur pourrait consulter et n'interagit jamais avec vos systèmes. Rien n'est exploité, aucune connexion n'est établie.",
  "You and bots":
    "Vous et les bots",
  "You need an approved <b>company or partner email</b>, the shared password, <b>and</b> a one-time code emailed to that inbox. Knowing the password isn't enough - you must own the mailbox.":
    "Il vous faut une <b>adresse e-mail d'entreprise ou de partenaire</b> agréée, le mot de passe partagé <b>et</b> un code à usage unique envoyé à cette boîte. Connaître le mot de passe ne suffit pas - vous devez posséder la boîte.",
  "You never type an IP, a network or a certificate. The robot resolves the target's ":
    "Vous ne saisissez jamais d'adresse IP, de réseau ni de certificat. Le robot détermine lui-même ",
  "Your answers are the ONE sanctioned way scope changes after a run":
    "Vos réponses sont le SEUL moyen autorisé de modifier le périmètre après une exécution",
  "Your company name. No access, no questionnaire, no NDA to start, and nothing to install. The euro figures are modelled ranges with the assumptions shown.":
    "Le nom de votre entreprise. Aucun accès, aucun questionnaire, aucun NDA pour commencer et rien à installer. Les montants en euros sont des fourchettes modélisées, dont les hypothèses sont affichées.",
  "Your whole internet-facing estate, discovered from public data":
    "L'intégralité de votre parc exposé sur Internet, découvert à partir de données publiques",
  "ZERO-TRUST":
    "ZERO TRUST",
  "Zero-trust login (2FA)":
    "Connexion zero trust (2FA)",
  "[auto] 9 ASNs / 41 domains / internal-CA VW-CA-PROC-09 / sweeping Shodan...":
    "[auto] 9 ASN / 41 domaines / CA interne VW-CA-PROC-09 / balayage Shodan...",
  "already public":
    "déjà public",
  "already running":
    "déjà lancés",
  "assessment bot":
    "bot d'analyse",
  "auto-discovery":
    "découverte automatique",
  "backups":
    "sauvegardes",
  "bgpview/RIPE/crt.sh":
    "bgpview/RIPE/crt.sh",
  "bot / online":
    "bot / en ligne",
  "build/scan/ship":
    "build / scan / livraison",
  "cassandra":
    "cassandra",
  "cybergod.ai cabinet":
    "espace cybergod.ai",
  "deliver, then refine":
    "livrer, puis affiner",
  "dive":
    "approfondie",
  "down":
    "de bout en bout",
  "email+pw+code":
    "email+pw+code",
  "entire":
    "toute",
  "events.log to <code>promtail</code> to Loki to Grafana (<code>godeyes.ai/observe</code>)":
    "events.log vers <code>promtail</code> vers Loki vers Grafana (<code>godeyes.ai/observe</code>)",
  "godeyes.ai/observe":
    "godeyes.ai/observe",
  "live":
    "direct",
  "machine":
    "machine",
  "multi-vendor chain":
    "chaîne multi-éditeurs",
  "paid / 30+ filters":
    "payant / plus de 30 filtres",
  "portfolio ALE EUR 11M-29M":
    "portefeuille ALE 11-29 M EUR",
  "recon to decks":
    "de la reconnaissance aux présentations",
  "research assistant":
    "assistant de recherche",
  "self-patch /3d":
    "auto-mise à jour / 3 j",
  "the assessor":
    "l'analyste",
  "until high-risk obligations apply · 2 Aug 2026":
    "avant l'application des obligations à haut risque · 2 août 2026",
  "until incident & vulnerability reporting · 11 Sep 2026":
    "avant la notification des incidents et des vulnérabilités · 11 septembre 2026",
  "until the BSI registration grace period ends · 31 Jul 2026":
    "avant la fin du délai de grâce d'enregistrement auprès du BSI · 31 juillet 2026",
  "value the fix buys back":
    "valeur récupérée par la correction",
  "zero-trust login":
    "connexion zero trust",
  "“How accurate is it?”":
    "«\u00a0Quelle est sa fiabilité\u00a0?\u00a0»",
  "“Is this legal?”":
    "«\u00a0Est-ce légal\u00a0?\u00a0»",
  "“What do we have to provide?”":
    "«\u00a0Que devons-nous fournir\u00a0?\u00a0»",
  "€10m / 2% of turnover":
    "€10m / 2% du chiffre d'affaires",
  "€15m / 2.5% of turnover":
    "€15m / 2.5% du chiffre d'affaires",
  "€35m / 7% of turnover":
    "€35m / 7% du chiffre d'affaires",
};
