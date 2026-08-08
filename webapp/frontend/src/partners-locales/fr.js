// partners-locales/fr.js : the FRENCH translation of en.js.
//
// en.js is the REFERENCE. Everything here is a translation of it and nothing else: the object
// shape (the three exports, the section ids and their order, the number of columns per section
// and the number of bullets per column) is asserted by tools/partners_gate.mjs, so a structural
// difference is a failed build rather than a customer noticing a missing column.
//
// Only TEXT is translated. `id`, `group`, `accent`, the `k` values inside change.cells and the
// `n` values in arts are LOOKUP KEYS and stay exactly as in the reference. Translating a lookup
// key makes content silently vanish.
//
// House rules that apply here too: no long dashes, no HTML entities (React escapes them, so they
// would reach the screen verbatim), no prices, no currency figures, no seat counts.

export const meta = {
  docTitle: "À qui cela s'adresse",
  kicker: "Un nom d'entreprise en entrée. Quatre documents prêts pour le comité en sortie. Onze publics.",
  h1a: "Saisissez un nom d'entreprise.",
  h1b: "Obtenez ",
  h1c: "toute la cartographie du risque",
  h1d: " en quelques minutes.",
  lede:
    "Pas un seul paquet n'est envoyé à l'entreprise évaluée. Tout est construit à partir de sources " +
    "que tout chercheur peut légalement consulter. Il n'y a donc rien à installer, personne à qui " +
    "demander une autorisation et aucun questionnaire à attendre. Quatre documents sont livrés à " +
    "chaque fois.",
  artsNote:
    "Il existe aussi un cinquième document : un rapport web autonome qui réunit les quatre autres " +
    "et s'ouvre dans n'importe quel navigateur. C'est celui que l'on fait circuler en interne. " +
    "Chaque document est disponible en anglais, en allemand ou en russe.",
  railTitle: "À qui cela s'adresse",
  groupPartners: "Partenaires",
  groupBuyers: "Acheteurs",
  groupEngage: "Comment travailler ensemble",
  foot:
    "Le contenu provient des supports destinés aux partenaires et aux régulateurs ainsi que du " +
    "dossier juridique signé. Aucun prix, aucune remise, aucun nombre de postes et aucun engagement " +
    "n'apparaissent nulle part, par choix. Les volumes de rendez-vous sont ceux rapportés par les " +
    "partenaires eux-mêmes et dépendent de chaque commercial. Les résultats d'une évaluation ne " +
    "constituent pas un conseil juridique. Toute référence à un client identifié est supprimée.",
};

export const arts = [
  { n: "1", name: "Constats", body:
    "Chaque exposition visible depuis Internet, classée de Critique à Faible. Chacune indique de " +
    "quoi il s'agit, pourquoi cela compte, comment y remédier, ainsi que l'adresse et le port " +
    "exacts sur lesquels elle a été observée." },
  { n: "2", name: "Le risque chiffré", body:
    "Les mêmes constats exprimés en montants, selon la méthode reconnue Factor Analysis of " +
    "Information Risk. Coût d'un incident, pire scénario annuel, et une courbe qui baisse à mesure " +
    "que les constats sont clôturés. Rédigé pour le directeur financier." },
  { n: "3", name: "Acteurs de la menace", body:
    "Quels attaquants sont réellement pertinents pour ce secteur et ces pays, et comment ils " +
    "opèrent. La réponse au conseil d'administration qui demande qui viendrait nous attaquer." },
  { n: "4", name: "Conformité", body:
    "Les constats rattachés aux articles des lois applicables là où l'entreprise opère, avec les " +
    "échéances réelles. Union européenne et Canada aujourd'hui." },
];

export const sections = [
  // ------------------------------------------------------------------ MANAGED SERVICE PROVIDERS
  {
    id: "msp", group: "partners", nav: "Fournisseurs de services managés",
    eyebrow: "Partenaire", h2: "Pour les fournisseurs de services managés",
    scr: {
      s: "Vous assurez la sécurité de nombreux clients à la fois, avec une équipe qui ne peut pas grandir aussi vite que votre portefeuille.",
      c: "Examiner à la main l'exposition d'un seul client coûte environ une journée d'analyste. À grande échelle cela ne se fait pas, et la revue trimestrielle devient un point d'avancement sur lequel personne n'engage de budget.",
      a: "Évaluez tous les clients de votre portefeuille au même rythme, pour un coût qui n'augmente pas avec leur nombre. Puis vendez la remédiation à quatre niveaux de prix distincts.",
    },
    cols: [
      { h: "1. Ce que vous vendez", li: [
        "L'évaluation elle-même, facturée, sous votre propre marque.",
        "Une reconduction mensuelle ou trimestrielle avec un rapport des changements. Ce rapport, c'est le service managé.",
        "Des licences, vendues par lots ou en illimité, sur lesquelles vous gagnez à part entière.",
      ] },
      { h: "2. Pourquoi l'économie fonctionne", li: [
        "Un analyste couvre tout votre portefeuille au lieu d'un seul compte.",
        "Démarrer chez un client ne demande rien de sa part : aucun logiciel à installer, aucun accès, aucun formulaire.",
        "Le document de conformité répond à l'auditeur dans la même exécution, il n'y a donc pas de seconde mission à staffer.",
      ] },
      { h: "3. Où se trouve la marge", li: [
        "Pas dans le rapport. Dans les quatre façons de clôturer un constat, exposées ci-dessous.",
        "Vos chargés de compte obtiennent une raison d'appeler chaque client, chaque mois, avec du concret.",
        "Un constat clôturé prouve que le contrat de service fonctionne, ce qui est la chose la plus difficile à démontrer en sécurité.",
      ] },
    ],
    ladder: { h: "Les quatre façons de clôturer un constat, de la moins chère à la plus chère", items: [
      { b: "Le conseil.", t: "Un atelier qui passe chaque constat en revue au regard de ce que le client possède déjà." },
      { b: "Aucune dépense nouvelle, avec son propre équipement.", t: "La plupart des constats se clôturent par des changements de configuration, de positionnement et de processus sur des produits déjà payés. Vous livrez une liste d'actions, chacune rattachée à l'outil qui la résout." },
      { b: "L'open source.", t: "Là où l'équipement existant ne suffit pas, une conception fondée sur l'open source plutôt qu'un achat. Il n'y a aucune licence à acheter. Le coût se déplace vers les compétences et l'exploitation, que le client recrute ou vous achète." },
      { b: "Un produit commercial.", t: "Uniquement là où aucune des options précédentes ne fonctionne. Le choix reste dans la liste des fournisseurs approuvés du client. Vous conseillez sur l'adéquation, la séquence et l'intégration." },
    ] },
    win: { h: "L'argument, dit simplement", p:
      "Un rapport unique, c'est un projet. Un rapport mensuel des changements, c'est un abonnement. " +
      "Vous vendez le constat et le chemin pour le corriger, à quatre niveaux de prix, à un client " +
      "qui vous fait déjà confiance." },
    steps: [
      { k: "Semaine 1", v: "Lancez vos dix plus gros comptes et lisez ce qui remonte." },
      { k: "Semaine 2", v: "Envoyez un constat à chacun. Voir la méthode ci-dessous." },
      { k: "Semaine 3", v: "Apposez votre marque et intégrez le prix à votre offre managée." },
    ],
    cta: { btn: "Parlons-en", txt: "Lots de licences, formules illimitées, paliers et conditions relèvent du commercial. Demandez-nous." },
  },

  // ------------------------------------------------------------------------------- RESELLERS
  {
    id: "var", group: "partners", nav: "Revendeurs",
    eyebrow: "Partenaire", h2: "Pour les revendeurs",
    scr: {
      s: "Vous vendez de la technologie, et vous gagnez sur la relation, le moment choisi et la qualité de la conversation que vous savez engager.",
      c: "Le premier rendez-vous technique est la chose la plus difficile à obtenir. Le substitut habituel est la remise, qui vous coûte de la marge et apprend au client à attendre la suivante.",
      a: "Entrez en sachant déjà ce qui est exposé sur leur périmètre. Facturez l'évaluation à son juste prix, puis déduisez sa valeur des travaux qu'elle révèle.",
    },
    cols: [
      { h: "1. Comment c'est facturé", li: [
        "L'évaluation est une prestation payante, à périmètre fixe. Ce n'est pas un cadeau.",
        "Sa valeur est ensuite déduite du conseil ou de la remédiation qui suivent.",
        "Le client ne prend donc aucun risque, et vous êtes payé dans tous les cas.",
      ] },
      { h: "2. Vos autres sources de revenu", li: [
        "Les licences, par lots ou en illimité, comme seconde ligne récurrente.",
        "Les quatre façons de clôturer un constat : le conseil, leur propre équipement, l'open source ou un produit approuvé.",
        "Les exécutions répétées, qui montrent ce qui a changé et relancent la conversation à date fixe.",
      ] },
      { h: "3. Ce qu'y gagne votre équipe commerciale", li: [
        "Une raison d'appeler n'importe qui, avec quelque chose de précis à dire.",
        "De nouveaux logos : aucune autorisation ni aucun accès ne sont nécessaires, vous pouvez donc travailler avant même d'être invité.",
        "La défense du renouvellement : lancez l'évaluation avant l'échéance d'un concurrent et montrez ce qui a changé.",
      ] },
    ],
    win: { h: "L'argument, dit simplement", p:
      "Une remise achète une affaire. En savoir plus qu'eux sur leur propre périmètre achète la " +
      "relation, et cette fois vous êtes payé pour le travail qui vous a ouvert la porte." },
    steps: [
      { k: "Jour 1", v: "Choisissez cinq prospects chez qui vous n'obtenez pas de rendez-vous." },
      { k: "Jour 2", v: "Envoyez un constat à chacun. Jamais le rapport." },
      { k: "Jour 5", v: "Prenez le rendez-vous. Facturez l'évaluation. Déduisez-la ensuite." },
    ],
    cta: { btn: "Parlons-en", txt: "Apport d'affaires, revente, licence et marque blanche : toutes les voies existent. Conditions sur demande." },
  },

  // ------------------------------------------------------------------------------ THE METHOD
  {
    id: "play", group: "partners", nav: "La méthode d'approche", accent: "gold",
    eyebrow: "Chaque partenaire l'utilise", h2: "Envoyez un seul constat. Gardez le rapport.",
    scr: {
      s: "Vous avez lancé l'évaluation et vous tenez un document qui contient tout.",
      c: "Un prospect qui n'a rien demandé lit un rapport comme un document commercial et le met de côté. Un rapport complet réclame en plus un créneau de réunion que personne n'a ce trimestre.",
      a: "Envoyez exactement un constat, avec sa preuve et la façon d'y remédier. C'est ce constat unique qui vous obtient le rendez-vous. Le rapport, c'est ce que vous vendez pendant ce rendez-vous.",
    },
    quote: {
      q: "Je ne vois pas du tout cette adresse dans notre inventaire d'actifs.",
      by: "Un ingénieur sécurité réseau d'un grand groupe régulé, assistant à une exécution en " +
          "direct. La plateforme avait fait apparaître une adresse attribuée à sa propre " +
          "organisation. Il n'a pas pu la retrouver dans le registre interne des actifs. " +
          "Entreprise, secteur et détails non communiqués.",
    },
    cols: [
      { h: "Comment procéder", li: [
        "Lancez l'évaluation, lisez les constats et choisissez-en exactement un.",
        "Envoyez ce constat, avec la preuve et le conseil pour le corriger.",
        "Ne joignez pas le rapport. Retirez les détails identifiants si l'approche est à froid.",
        "Demandez trente minutes pour parcourir le reste.",
      ] },
      { h: "Pourquoi un constat vaut mieux qu'un rapport", li: [
        "**Un actif inconnu est le constat le plus fort qui soit.** Une adresse absente du registre des actifs échappe aux correctifs, aux analyses et au reporting, et l'inventaire des actifs se trouve à la base de toutes les normes de sécurité sur lesquelles ils sont audités.",
        "**Il résiste au scepticisme.** Un constat connu appelle un \"c'est une autre équipe qui s'en occupe\". Une adresse que personne ne sait expliquer ne se traite pas ainsi.",
        "**Il correspond à votre interlocuteur.** Il touche l'équipe à qui vous parlez déjà, et non un service que personne dans la salle ne dirige.",
        "**Il justifie son propre prix.** Une machine non administrée exposée sur Internet coûte peu à discuter et cher à ignorer.",
      ] },
    ],
    win: { h: "Ce que rapportent les partenaires", p:
      "Les partenaires en Allemagne et en Suisse qui appliquent cette méthode font état de six à " +
      "dix nouveaux premiers rendez-vous par commercial et par semaine. Cela dépend clairement de " +
      "la capacité de chaque vendeur à transformer un fait en conversation, aussi préférons-nous " +
      "que vous l'entendiez de leur bouche. Nous organiserons l'appel." },
    cta: { btn: "Demander un appel de référence", ghost: true, txt: "Partenaires de référence disponibles sur le marché germanophone." },
  },

  // --------------------------------------------------------------------- SYSTEMS INTEGRATORS
  {
    id: "gsi", group: "partners", nav: "Intégrateurs de systèmes",
    eyebrow: "Partenaire", h2: "Pour les intégrateurs de systèmes",
    scr: {
      s: "La découverte est la première phase de chaque programme de sécurité et de transformation que vous menez.",
      c: "Elle est facturée au tarif consultant, réalisée à la main, différente à chaque mission, et c'est la facture que les clients contestent. Pourtant, rien de ce qui suit n'est valable sans elle.",
      a: "Faites de la découverte une étape fixe, rapide et identique sur chaque mission, pour que votre marge se déplace vers l'architecture et la remédiation, là où elle doit être.",
    },
    cols: [
      { h: "1. Sa place dans votre méthodologie", li: [
        "La découverte devient une entrée de votre méthodologie, pas un remplacement de celle-ci.",
        "Une référence au démarrage du programme, puis une reprise à chaque jalon.",
        "L'avancement se prouve par ce qui a été clôturé, au lieu d'être affirmé dans un rapport d'état.",
      ] },
      { h: "2. Où elle s'applique aussi", li: [
        "Évaluer un fournisseur sans attendre qu'il coopère.",
        "Cadrer une société tout juste acquise avant de raccorder son réseau à celui du groupe.",
        "Tout pays ou toute filiale où vous n'avez pas d'équipe locale.",
      ] },
      { h: "3. Ce que cela change commercialement", li: [
        "Vous cessez de vendre des semaines de collecte de faits et vendez le résultat qu'elles bloquaient.",
        "Le document financier chiffre le programme dans la langue du directeur financier dès le premier jour.",
        "Chaque constat porte sa preuve, il résiste donc à la revue technique du client.",
      ] },
    ],
    win: { h: "L'argument, dit simplement", p:
      "La première facture cesse d'être celle que votre client conteste, car elle achète désormais " +
      "une réponse et non une activité." },
    steps: [
      { k: "Étape 1", v: "Lancez-la sur une mission en cours et comparez avec ce que votre équipe a trouvé à la main." },
      { k: "Étape 2", v: "Intégrez-la à votre livrable de découverte standard." },
      { k: "Étape 3", v: "Apposez votre marque, ou intégrez-la. Voir les deux modèles en fin de page." },
    ],
    cta: { btn: "Parlons-en", txt: "Les conditions de volume, régionales et d'intégration relèvent du commercial. Demandez-nous." },
  },

  // ------------------------------------------------------------------------------- VENDORS
  {
    id: "vendors", group: "partners", nav: "Éditeurs de cybersécurité",
    eyebrow: "Partenaire", h2: "Pour les éditeurs de cybersécurité",
    scr: {
      s: "Vous avez un produit qui résout un vrai problème, et une démonstration qui le montre à l'oeuvre.",
      c: "Votre démonstration prouve que le produit fonctionne en général. Elle ne prouve pas que ce client a le problème aujourd'hui, si bien que l'évaluation se réduit à une comparaison de fonctionnalités face à un concurrent.",
      a: "Montrez au prospect ce qui est ouvert sur son propre périmètre avant de lui montrer votre produit. Puis relancez l'évaluation après le déploiement et montrez, en montants, ce que votre produit a refermé.",
    },
    cols: [
      { h: "1. Dans votre propre équipe commerciale", li: [
        "Chaque chargé de compte dispose d'une cartographie d'exposition propre à ce client.",
        "Elle ouvre des portes chez des entreprises qui ne vous connaissent pas, sans aucun accès requis.",
        "Le document financier transforme une exposition technique en ligne budgétaire.",
      ] },
      { h: "2. À l'intérieur de votre produit", li: [
        "L'exposition externe devient une fonctionnalité de votre plateforme, livrée via notre interface de programmation.",
        "Votre interface, votre marque, aucun second produit à faire évaluer par le client.",
        "Elle ajoute une vue de l'extérieur à un produit qui regarde surtout vers l'intérieur, ce qui est un vrai manque dans la plupart des dispositifs de sécurité.",
      ] },
      { h: "3. À côté de votre produit", li: [
        "Lancez-la avant et après le déploiement. L'écart, c'est votre étude de cas.",
        "Elle donne aux renouvellements un chiffre plutôt qu'une impression.",
        "Vous pouvez aussi revendre des licences à côté de vos propres produits.",
      ] },
    ],
    win: { h: "L'argument, dit simplement", p:
      "Personne ne conteste sa propre surface d'attaque. C'est le chemin le plus court entre une " +
      "démonstration et un budget." },
    steps: [
      { k: "Évaluer", v: "Lancez-la sur trois de vos affaires en cours." },
      { k: "Décider", v: "Outil commercial, ligne de revente, ou fonctionnalité de votre plateforme." },
      { k: "Intégrer", v: "Les constats arrivent dans votre produit via l'interface de programmation." },
    ],
    cta: { btn: "Parlons-en", txt: "Les conditions d'intégration et de licence dépendent du volume et de la profondeur d'intégration. Demandez-nous." },
  },

  // ---------------------------------------------------------------------------- CONSULTING
  {
    id: "consulting", group: "partners", nav: "Cabinets de conseil",
    eyebrow: "Partenaire", h2: "Pour les cabinets de conseil",
    scr: {
      s: "Vous vendez du jugement et de l'indépendance. Les clients paient pour l'avis et pour le nom sur la couverture.",
      c: "La collecte des faits consomme l'essentiel de la mission et c'est la partie que les clients veulent le moins payer. Vous facturez des juniors pour rassembler des faits et des associés pour les interpréter, et seul le second travail est valorisé.",
      a: "Réduisez la collecte des faits de plusieurs semaines à quelques jours, apposez votre marque sur les livrables et vendez l'interprétation.",
    },
    cols: [
      { h: "1. Ce que vous pouvez vendre", li: [
        "Une première mission payante, livrée en quelques jours, qui ouvre la plus grande.",
        "Un second avis indépendant sur un programme de sécurité déjà lancé.",
        "Des licences pour que le client continue à l'utiliser, sur lesquelles vous gagnez.",
      ] },
      { h: "2. Ce que vous laissez derrière vous", li: [
        "Les constats pour le directeur de la sécurité.",
        "Le risque chiffré pour le directeur financier.",
        "Les acteurs de la menace pour le conseil, et la conformité pour le comité d'audit.",
      ] },
      { h: "3. Pourquoi vous pouvez le signer sans crainte", li: [
        "Lorsqu'une source n'a pas pu être atteinte, le constat indique \"inconnu\" au lieu d'inventer une faiblesse.",
        "Chaque constat porte la preuve sur laquelle il repose, et la date de son observation.",
        "C'est reproductible, la mission suivante part donc d'un point de départ mesuré.",
      ] },
    ],
    win: { h: "L'argument, dit simplement", p:
      "C'est votre nom qui figure sur le document. C'est précisément pour cela qu'une méthode qui " +
      "refuse de deviner vaut plus, pour vous, qu'une méthode qui produit toujours un chiffre." },
    steps: [
      { k: "Pilote", v: "Un client, une exécution, votre propre analyse par-dessus." },
      { k: "Offre", v: "Une offre nommée, à périmètre fixe et prix fixe." },
      { k: "Marque", v: "Votre identité sur la plateforme et sur chaque document." },
    ],
    cta: { btn: "Parlons-en", txt: "Marque blanche, licence et conditions de volume sur demande." },
  },

  // --------------------------------------------------------------------------------- TELCO
  {
    id: "telco", group: "partners", nav: "Opérateurs télécoms",
    eyebrow: "Partenaire", h2: "Pour les opérateurs télécoms",
    scr: {
      s: "Vous vendez de la connectivité à des milliers d'entreprises et vous voulez y attacher de la sécurité avant que la connectivité ne devienne une pure commodité.",
      c: "Une activité de sécurité managée exige des analystes que vous ne pouvez pas recruter, à une marge que le marché ne paiera pas, pour une base de clients bien trop large pour être servie un par un.",
      a: "Vendez un service de sécurité dont le coût n'augmente pas avec le nombre de clients, délivré par les chargés de compte que vous employez déjà.",
    },
    cols: [
      { h: "1. Ce que vous vendez", li: [
        "Un service d'évaluation à votre marque : votre portail, votre facture, votre prix.",
        "Des licences en ligne récurrente, par lots ou en illimité.",
        "Une revue récurrente qui rend le contrat de connectivité plus difficile à quitter que le seul prix.",
      ] },
      { h: "2. Comment cela atteint la base", li: [
        "Attachez-le au moment de la vente, pendant la signature de la commande de connectivité.",
        "Aucun nouveau geste commercial : vos chargés de compte actuels sont le canal.",
        "Cela atteint la longue traîne de petits clients que vous ne pourrez jamais servir avec des humains.",
      ] },
      { h: "3. Où cela s'exécute", li: [
        "Dans votre propre environnement, ou dans un cloud national si la réglementation l'exige.",
        "Dans le pays désigné par votre régulateur, serveur de licences compris.",
        "Dans les langues que votre marché lit réellement.",
      ] },
    ],
    win: { h: "L'argument, dit simplement", p:
      "C'est la rare offre de sécurité qu'une base de clients de votre taille peut réellement " +
      "absorber, parce que rien n'y exige un analyste par client." },
    steps: [
      { k: "Prouver", v: "Lancez-la sur un échantillon de votre propre base." },
      { k: "Marquer", v: "Habillez la plateforme et chaque document à vos couleurs." },
      { k: "Attacher", v: "Placez-la sur le bon de commande de connectivité." },
    ],
    cta: { btn: "Parlons-en", txt: "Marque blanche, intégration, licence et conditions de volume sur demande." },
  },

  // ----------------------------------------------------------------------------------- SME
  {
    id: "sme", group: "buyers", nav: "Petites et moyennes entreprises",
    eyebrow: "Acheteur", h2: "Pour les petites et moyennes entreprises",
    note:
      "Une petite ou moyenne entreprise désigne ici une société d'environ dix à deux cent cinquante " +
      "salariés, où une seule personne s'occupe de l'informatique en plus d'un autre poste. Cette " +
      "page est écrite pour cette entreprise elle-même : le dirigeant, le gérant, ou cette personne.",
    scr: {
      s: "On vous dit que votre entreprise doit prendre la cybersécurité au sérieux, et vous êtes d'accord.",
      c: "Le conseil habituel consiste à acheter un test d'intrusion, un consultant et un jeu de politiques. Les trois coûtent plus cher que le risque que personne n'a chiffré pour vous, et aucun ne répond à la seule question que vous vous posez vraiment.",
      a: "Découvrez ce qu'un inconnu peut voir de votre entreprise depuis l'extérieur, cette semaine, sans rien installer ni laisser entrer qui que ce soit dans votre réseau.",
    },
    cols: [
      { h: "1. Ce que vous recevez", li: [
        "Tout ce qui vous appartient et qui est visible depuis Internet, y compris ce que plus personne n'avait en tête.",
        "Ce que cela vous coûterait si cela tournait mal, en montants, avec la méthode exposée.",
        "Quelles lois s'appliquent à vous et à quelle échéance, en langage clair.",
      ] },
      { h: "2. Pourquoi cela convient à une entreprise de votre taille", li: [
        "Rien à installer. Aucun logiciel, aucun accès, personne ne vient dans vos locaux.",
        "Vous donnez un nom d'entreprise. C'est tout le paramétrage.",
        "Relancez-la dès que quelque chose change, au lieu d'une fois par an quand vous en avez les moyens.",
      ] },
      { h: "3. Ce que vous pouvez en faire", li: [
        "La transmettre telle quelle à un client qui vous audite.",
        "La remettre à votre banque ou à votre assureur sans traduction.",
        "La donner à votre prestataire informatique comme liste de travaux.",
      ] },
    ],
    channel: {
      b: "Comment l'acheter.",
      t: "Par un partenaire, et non directement chez nous. Choisissez l'un de nos partenaires " +
         "certifiés dans votre région, ou présentez-nous la société informatique en qui vous avez " +
         "déjà confiance et nous l'intégrerons. Vous gardez la relation que vous avez. Elle gagne " +
         "la capacité. Le choix vous appartient.",
    },
    win: { h: "L'argument, dit simplement", p:
      "La plupart des entreprises de votre taille découvrent au moins une chose qu'elles ignoraient " +
      "être visible depuis Internet. La trouver vous coûte un après-midi plutôt qu'un projet." },
    steps: [
      { k: "Maintenant", v: "Regardez la démonstration publique. Documents réels, entreprise inventée." },
      { k: "Ensuite", v: "Demandez-nous, ou demandez à votre prestataire, une exécution sur votre propre nom." },
      { k: "Après", v: "Corrigez ce qui compte, puis relancez pour prouver que c'est clôturé." },
    ],
    cta: { btn: "Trouver un partenaire", txt: "Les prix et les conditions viennent de votre partenaire. Dites-nous votre région et nous vous présenterons quelqu'un, ou amenez le vôtre." },
  },

  // ---------------------------------------------------------------------------- ENTERPRISE
  {
    id: "enterprise", group: "buyers", nav: "Grandes entreprises",
    eyebrow: "Acheteur", h2: "Pour les grandes entreprises",
    scr: {
      s: "Vous avez des équipes de sécurité, des outils matures et un vrai budget. Chacune de ces équipes détient une partie du tableau.",
      c: "Personne ne sait dire à quoi ressemble l'ensemble du groupe vu de l'extérieur, ni le prouver. Filiales et acquisitions laissent des actifs qu'aucune équipe ne revendique. Le risque fournisseur s'évalue avec un formulaire que le fournisseur remplit sur lui-même.",
      a: "Une vue externe unique de tout le groupe, chiffrée en montants, répétée à intervalles réguliers, avec un rapport de ce qui a exactement changé depuis la fois précédente.",
    },
    cols: [
      { h: "1. Une couverture que vos outils n'ont pas", li: [
        "Tout le groupe, y compris les filiales et les marques qui ne portent pas le nom de la maison mère.",
        "Les fournisseurs évalués de la même façon, sans accès et sans questionnaire.",
        "Les sociétés tout juste acquises, avant que leur réseau ne rejoigne le vôtre.",
      ] },
      { h: "2. Des livrables au format de votre organisation", li: [
        "Les constats pour la sécurité réseau. Le risque chiffré pour le directeur financier et le comité des risques.",
        "Les acteurs de la menace pour le conseil. La conformité pour l'audit interne.",
        "Aucune équipe n'a besoin de l'accord d'une autre pour utiliser son propre document.",
      ] },
      { h: "3. Conçu pour résister à la contestation", li: [
        "Chaque constat porte l'adresse, le port, la preuve et la date.",
        "Le cadrage est volontairement prudent : le serveur d'une autre entreprise sur une infrastructure partagée n'est jamais rapporté comme le vôtre.",
        "Lorsqu'une source n'a pas pu être atteinte, il indique \"inconnu\" plutôt que de déduire une faiblesse.",
      ] },
    ],
    change: {
      h: "Le rapport des changements, qui est la partie qui compte",
      lead:
        "Une évaluation isolée vous dit où vous en êtes. Elle ne peut pas vous dire si quoi que ce " +
        "soit s'améliore. Relancez-la et la plateforme compare les deux exécutions et ne rapporte que ce qui a bougé.",
      cells: [
        { k: "new", t: "Nouveau", b: "n'existaient pas la fois précédente",
          before: "Des expositions qui ", after: " : un service que quelqu'un a publié, un certificat arrivé à expiration, un serveur apporté par une acquisition." },
        { k: "closed", t: "Clôturé", b: "ont disparu",
          before: "Des constats qui ", after: ". C'est la preuve qu'un budget de remédiation a produit un résultat, ce qui est la chose la plus difficile à démontrer en sécurité." },
        { k: "open", t: "Toujours ouvert", b: "n'ont pas bougé",
          before: "Des constats déjà signalés qui ", after: ", avec leur ancienneté. C'est la liste d'escalade, et elle s'écrit toute seule." },
      ],
      tailBefore: "Votre processus de conformité ne veut pas un rapport. Il veut une réponse datée et prouvée à une seule question : ",
      tailBold: "qu'est-ce qui a changé, et quelqu'un a-t-il corrigé ce que nous avions signalé ?",
      tailAfter: " C'est ce qui transforme cet exercice en contrôle plutôt qu'en projet, et c'est la raison de le lancer à intervalles réguliers plutôt qu'une seule fois.",
    },
    channel: {
      b: "Comment l'acheter.",
      t: "Par le canal partenaire. Choisissez l'un de nos partenaires certifiés, ou désignez " +
         "l'intégrateur avec lequel vous travaillez déjà et nous l'intégrerons. Votre processus " +
         "d'achat, vos contrats et vos relations fournisseurs existantes restent tels quels.",
    },
    win: { h: "L'argument, dit simplement", p:
      "Vos équipes gardent tous leurs outils. Ceci répond à la seule question vers laquelle aucun " +
      "de ces outils n'est tourné : ce que le monde extérieur voit de tout ce que vous possédez. " +
      "Puis cela prouve, mois après mois, si cela se réduit." },
    steps: [
      { k: "Prouver", v: "Une entité du groupe. Comparez-la avec ce que vous pensiez posséder." },
      { k: "Étendre", v: "Ajoutez les filiales et vos fournisseurs les plus critiques." },
      { k: "Exploiter", v: "Mettez-la à intervalles réguliers et pilotez le rapport des changements." },
    ],
    cta: { btn: "Parlons-en", txt: "Les accords grands comptes, l'accès à l'interface de programmation et la documentation de sécurité passent par votre partenaire ou par le nôtre." },
  },

  // ----------------------------------------------------------------------------------- LAW
  {
    id: "law", group: "buyers", nav: "Cabinets d'avocats",
    eyebrow: "Acheteur", h2: "Pour les cabinets d'avocats",
    scr: {
      s: "Vous conseillez en protection des données, incidents cyber, fusions et acquisitions, et exposition réglementaire.",
      c: "Vous avez régulièrement besoin de faits techniques sur une entreprise que vous n'avez aucune autorité pour toucher. Tester les systèmes d'un tiers sans autorisation crée exactement la responsabilité que vous existez pour éviter.",
      a: "Des preuves techniques obtenues sans rien faire à personne, ce qui est précisément ce qui les rend utilisables dans votre travail.",
    },
    cols: [
      { h: "1. Où cela s'applique", li: [
        "**Audit préalable dans une transaction :** le véritable patrimoine externe de la cible, et son risque chiffré, avant la signature du contrat d'acquisition.",
        "**Après un incident :** une image indépendante et datée de ce qui était publiquement visible.",
        "**Contentieux :** une pièce technique qu'un autre expert peut reproduire.",
      ] },
      { h: "2. Pourquoi son usage est licite", li: [
        "Entièrement passif. Pas un seul paquet n'atteint l'entreprise évaluée.",
        "Rien n'est exploité et aucune connexion n'est établie.",
        "Construit uniquement à partir de sources que tout chercheur peut légalement consulter, aucune autorisation n'est donc requise de qui que ce soit.",
      ] },
      { h: "3. Ce que vous pouvez présenter à un client", li: [
        "Chaque constat avec sa preuve et la date de son obtention.",
        "Quelles réglementations s'appliquent, avec les obligations et les échéances citées des textes d'origine.",
        "L'exposition convertie en un montant que le conseil de votre client comprend.",
      ] },
    ],
    win: { h: "L'argument, dit simplement", p:
      "Cela produit des faits techniques dotés de la seule propriété qu'exige votre travail : ils " +
      "ont été obtenus sans rien faire à personne. C'est ce qui les rend utilisables." },
    steps: [
      { k: "Évaluer", v: "Lancez-la sur un dossier que vous conseillez déjà." },
      { k: "Vérifier", v: "Confrontez la chaîne de preuve à vos propres exigences." },
      { k: "Adopter", v: "Faites-en une étape standard de l'audit préalable et du traitement des incidents." },
    ],
    cta: { btn: "Parlons-en", txt: "Conditions au dossier ou pour tout le cabinet, via le canal partenaire. Les livrables ne constituent pas un conseil juridique et ne remplacent pas un avocat." },
  },

  // ----------------------------------------------------------------------------- INSURANCE
  {
    id: "insurance", group: "buyers", nav: "Assureurs",
    eyebrow: "Acheteur", h2: "Pour les assureurs, agents et courtiers",
    scr: {
      s: "Vous souscrivez de la cyberassurance, et vous la tarifez à partir de ce que le proposant déclare sur lui-même.",
      c: "Le questionnaire est déclaratif, optimiste et périmé le jour de sa signature. Au renouvellement, vous ne savez pas si ce que l'assuré avait promis de corriger l'a été. Après un sinistre, vous ne pouvez pas montrer ce qui était visible.",
      a: "Souscrivez sur ce qui est observable plutôt que sur ce qui est déclaré, sur chaque risque, pour un coût qui n'augmente pas avec leur nombre.",
    },
    cols: [
      { h: "1. Quelle prime ce risque doit-il porter ?", li: [
        "Une perte attendue et un pire scénario annuel, produits par la méthode reconnue Factor Analysis of Information Risk.",
        "Le détail du calcul est montré, c'est donc une donnée technique pour votre décision de tarification et non une note issue d'une boîte noire.",
        "Disponible avant même que le proposant vous ait choisi, car cela ne demande aucune coopération.",
      ] },
      { h: "2. Qu'y a-t-il réellement sur son patrimoine ?", li: [
        "Chaque exposition visible depuis Internet, classée, avec l'adresse et le port.",
        "Indépendant du questionnaire, ce qui permet de comparer les deux.",
        "Livré en quelques minutes, cela tient donc dans un processus de cotation.",
      ] },
      { h: "3. Sont-ils conformes ?", li: [
        "Leur situation au regard des lois cyber qui leur sont applicables, avec les échéances.",
        "La non-conformité est à la fois un facteur de sinistre et une question de garantie.",
        "Les régimes de l'Union européenne et du Canada sont actifs aujourd'hui.",
      ] },
    ],
    ladder: { h: "Tout au long de la vie du contrat", items: [
      { b: "À la cotation.", t: "Quelques minutes, sans aucune coopération nécessaire." },
      { b: "Au renouvellement.", t: "Le rapport des changements montre la remédiation, ou son absence. Tarifez la différence." },
      { b: "Sur tout le portefeuille.", t: "Relancez tout le portefeuille dès qu'une nouvelle vulnérabilité largement exploitée apparaît, et connaissez votre exposition cumulée le jour même." },
      { b: "Au sinistre.", t: "Un relevé daté de ce qui était visible depuis l'extérieur." },
    ] },
    win: { h: "L'argument, dit simplement", p:
      "Vous passez de la souscription sur déclaration à la souscription sur observation, de façon " +
      "homogène, sur chaque risque. C'est un argument de ratio sinistres sur primes, pas un " +
      "argument technologique." },
    steps: [
      { k: "Étalonner", v: "Lancez-la sur des risques déjà souscrits, y compris ceux qui ont produit des sinistres." },
      { k: "Comparer", v: "Placez les résultats à côté des questionnaires et regardez les écarts." },
      { k: "Intégrer", v: "Dans le processus de cotation, ou dans votre portail courtiers." },
    ],
    cta: { btn: "Parlons-en", txt: "Conditions portefeuille, interface de programmation et intégration sur demande." },
  },

  // ----------------------------------------------------------------------------- REGULATOR
  {
    id: "regulator", group: "buyers", nav: "Régulateurs",
    eyebrow: "Acheteur", h2: "Pour les régulateurs et autorités de contrôle",
    scr: {
      s: "Vous supervisez une population d'entités au titre d'un mandat de cybersécurité ou de résilience opérationnelle.",
      c: "La loi est écrite et les échéances sont réelles. Vos moyens techniques ne le sont pas. En pratique, vous inspectez quelques entités par an, choisies sans base technique. Vous ne pouvez pas savoir si celles que vous n'avez pas inspectées sont celles qui comptent.",
      a: "Supervisez toute la population à partir de preuves publiques, sans vous déplacer chez personne, et transformez chaque manquement en dossier préparé que votre agent examine et signe.",
    },
    cols: [
      { h: "1. La couverture plutôt que l'échantillon", li: [
        "Chaque entité supervisée, évaluée par la même méthode le même jour.",
        "Les résultats sont comparables dans tout le secteur, car rien n'est mesuré différemment.",
        "Reproductible à intervalles réguliers, vous mesurez donc la trajectoire du secteur.",
      ] },
      { h: "2. Des preuves qui résistent à la contestation", li: [
        "Par entité : l'adresse, le port, la preuve et la date de l'observation.",
        "Rattachées à l'article précis qu'elles engagent.",
        "Lorsqu'une source ne peut être atteinte, le système indique \"inconnu\" et n'affirme aucun manquement.",
      ] },
      { h: "3. Licite par construction", li: [
        "Entièrement passif. Aucune entité n'est touchée, aucune notification ni autorisation n'est donc nécessaire.",
        "Reproductible, cela résiste donc à l'examen des propres experts de l'entité.",
        "Déployable dans votre propre environnement ou dans un environnement national si le mandat l'exige.",
      ] },
    ],
    ladder: { h: "La chaîne de sanction, appliquée à toute la population", items: [
      { b: "Détecter.", t: "Une situation de non-conformité chez une entité supervisée, avec l'adresse, le port et la date de l'observation." },
      { b: "Rattacher.", t: "L'article précis engagé, qu'il relève du droit européen ou de votre propre instrument national." },
      { b: "Corroborer.", t: "Quatre modèles d'intelligence artificielle indépendants, issus de quatre fournisseurs différents, examinent le dossier. Deux le construisent et deux tentent de le démonter. Ce sont des règles fixes inscrites dans le code qui décident, pas les modèles, et un dossier qu'aucun d'eux ne corrobore ne quitte jamais la file." },
      { b: "Rédiger.", t: "Le dossier probatoire et la notification de sanction sont préparés automatiquement." },
      { b: "Décider.", t: "Votre agent examine et signe. La machine construit le dossier et l'autorité le délivre, ce qui garantit que chaque notification reste examinable et susceptible de recours." },
    ] },
    win: { h: "L'argument, dit simplement", p:
      "Vous cessez de choisir qui inspecter d'après la réputation. Vous commencez à superviser tout " +
      "le secteur par la preuve, sans envoyer un inspecteur dans un seul bâtiment, et sans qu'un " +
      "seul paquet n'atteigne une entité supervisée." },
    steps: [
      { k: "Pilote", v: "Un secteur, un groupe d'entités. Classez-les." },
      { k: "Comparer", v: "Confrontez le classement à votre propre connaissance du terrain." },
      { k: "Étendre", v: "Toute la population, à intervalles réguliers, avec la file de sanction." },
    ],
    cta: { btn: "Parlons-en", txt: "Marchés publics, localisation de l'hébergement et conditions sur demande." },
  },

  // --------------------------------------------------------------------------- WHITE-LABEL
  {
    id: "whitelabel", group: "engage", nav: "Marque blanche", accent: "purple",
    eyebrow: "Comment travailler ensemble, modèle 1 sur 2", h2: "Marque blanche",
    scr: {
      s: "Vous voulez un service de sécurité à vendre sous votre propre nom.",
      c: "Construire le moteur prend des années. Revendre la marque d'un autre signifie que la relation client lui appartient, et non à vous.",
      a: "Votre marque en façade, notre moteur en dessous. Votre client, votre contrat, votre prix, et il ne nous voit jamais.",
    },
    cols: [
      { h: "Ce qui devient le vôtre", li: [
        "La marque sur chaque écran et sur les quatre documents.",
        "La relation client, le contrat et la facture.",
        "Votre propre tarification, fixée par vous, pour votre marché.",
        "Le lieu d'exécution : votre cloud, votre région, ou un environnement national. Le serveur de licences peut se trouver dans le pays ou la région de votre choix.",
      ] },
      { h: "Ce qui ne le devient pas", li: [
        "Le code source et la propriété de la plateforme. Vous recevez une licence pour l'utiliser et la présenter, pas pour la posséder.",
        "Le droit de concéder le logiciel lui-même à un tiers.",
        "Le développement du moteur et ses garanties d'exactitude. Ils restent chez nous, et c'est sur eux que vous vous appuyez.",
      ] },
    ],
    win: { h: "Choisissez ce modèle si", p:
      "Vous voulez un produit à vendre : quelque chose auquel votre client se connecte, à votre " +
      "nom. C'est le bon modèle pour les fournisseurs de services managés, les opérateurs télécoms, " +
      "les cabinets de conseil et les revendeurs qui construisent une activité de sécurité." },
    steps: [
      { k: "Cadrer", v: "Marque, région d'hébergement, langues, modules retenus." },
      { k: "Construire", v: "Nous l'habillons et la déployons. Vous la recettez selon des critères convenus." },
      { k: "Vendre", v: "Sous votre nom, à votre prix." },
    ],
    cta: { btn: "Parlons-en", txt: "Engagements, périmètre de mise en place et tarification sont commerciaux et confidentiels. Demandez-nous." },
  },

  // ----------------------------------------------------------------------------------- OEM
  {
    id: "oem", group: "engage", nav: "Intégré (OEM)", accent: "purple",
    eyebrow: "Comment travailler ensemble, modèle 2 sur 2", h2: "Intégré, également appelé OEM",
    scr: {
      s: "Vous avez déjà un produit auquel vos clients se connectent tous les jours.",
      c: "Vendre un produit séparé à côté crée des frictions : un autre identifiant, un autre contrat, une chose de plus à expliquer. Cela dilue aussi le produit que vous avez mis des années à construire.",
      a: "Notre moteur à l'intérieur de votre produit, pour que votre client voie une nouvelle fonctionnalité plutôt qu'un nouveau produit à évaluer.",
    },
    cols: [
      { h: "Comment cela fonctionne", li: [
        "Vous appelez notre interface de programmation. Constats, risque chiffré, contexte sur les acteurs de la menace, notations de conformité et documents finis reviennent sous forme de données.",
        "Vous les affichez dans votre propre interface, selon votre propre structure.",
        "Les constats critiques sont poussés vers votre plateforme ou votre système de supervision de sécurité au fil de l'eau, il n'y a donc rien à interroger.",
        "Déployable dans votre environnement, dans la région qu'exige votre architecture ou votre régulateur.",
      ] },
      { h: "Ce que cela vous apporte", li: [
        "Une nouvelle capacité dans un produit existant, sans nouvel élément à faire approuver par le client.",
        "Pas de second identifiant, pas de second contrat, pas de second canal de support.",
        "La maîtrise totale de l'expérience, de sa place dans votre feuille de route et de sa tarification.",
        "Vous pouvez toujours revendre des licences en ligne séparée lorsqu'un compte le demande.",
      ] },
    ],
    vs: {
      a: { h: "La marque blanche est", bold: "produit", before: "Un ", after: " qui a l'air d'être le vôtre. Votre client se connecte à quelque chose qui porte votre marque. Idéal quand vous construisez une activité de services et qu'il vous faut quelque chose à vendre." },
      b: { h: "L'intégré est", bold: "capacité", before: "Une ", after: " à l'intérieur de votre produit. Votre client voit une nouvelle fonctionnalité, pas un nouveau produit. Idéal quand vous possédez déjà l'écran que votre client regarde et que vous ne voulez pas en ajouter un second." },
    },
    win: { h: "Choisissez ce modèle si", p:
      "Vous êtes un éditeur de logiciels ou de sécurité, un assureur doté d'un portail, ou une " +
      "entreprise de plateforme. Le test est simple. Si votre client se connecte déjà à quelque " +
      "chose qui vous appartient, choisissez l'intégré. Sinon, choisissez la marque blanche." },
    steps: [
      { k: "Concevoir", v: "Quels appels, quelles données, à quel endroit." },
      { k: "Intégrer", v: "Clés limitées, rappels signés, spécification versionnée." },
      { k: "Livrer", v: "Cela devient une fonctionnalité de votre plateforme." },
    ],
    cta: { btn: "Parlons-en", txt: "Profondeur d'intégration, volume et conditions relèvent du commercial. Demandez-nous." },
  },

  // ------------------------------------------------------------------------------- CONTACT
  {
    id: "contact", group: "engage", nav: "Parlons-en",
    eyebrow: "Étape suivante", h2: "Parlons-en",
    note:
      "Prix, paliers, modèles de licence, engagements et conditions contractuelles sont commerciaux " +
      "et se conviennent directement. Ils ne sont volontairement pas publiés ici.",
    cols: [
      { h: "Ce que nous pouvons faire cette semaine", li: [
        "Une exécution en direct sur un nom d'entreprise que vous choisissez, pour que vous jugiez le résultat et non le discours.",
        "Un appel de référence avec un partenaire qui vend déjà cette offre sur le marché germanophone.",
        "Le dossier juridique : contrat de partenariat, avenant marque blanche et intégré, accord de confidentialité, engagement de niveau de service, conditions d'utilisation, accord de traitement des données et fiche d'hébergement.",
        "La documentation d'architecture de sécurité que votre responsable sécurité ou votre service achats demandera.",
      ] },
      { h: "Ce que nous vous demanderons", li: [
        "Lequel des publics ci-dessus vous êtes. Cela change nettement la réponse.",
        "Si vous souhaitez la revendre, y apposer votre marque, ou l'intégrer dans votre propre produit.",
        "Si vous vendez des licences, des services, ou les deux.",
        "Où les données, et le serveur de licences, doivent être situés.",
      ] },
    ],
    cta: { btn: "Écrivez-nous", ghost2: "Voir d'abord la démonstration publique", txt: "Cybergod LLC, membre du S4Biz Group" },
  },
];
