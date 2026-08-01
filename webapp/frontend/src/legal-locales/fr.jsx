// legal-locales/fr.jsx — see ./index.js. Missing exports fall back to English, then German.
// German is the NORMATIVE text; this is a reading translation.
//
// TRANSLATED FROM THE ENGLISH VARIANT IN ../legal.jsx, CROSS-CHECKED AGAINST THE GERMAN.
// Nothing here is a new legal instrument: every retention period (30 / 90 days), every legal basis
// (Art. 6(1)(b) / 6(1)(f)), the single non-EU recipient (Google / Gmail API under the EU-US Data
// Privacy Framework), the FRA1 / Frankfurt hosting claim, the DB-IP credit and the German statutes
// (§ 5 DDG, § 7(1) DDG, § 18(2) MStV, § 25(2)(2) TDDDG) are carried over EXACTLY. DSGVO article
// numbers are written as RGPD per French usage; the German statutes are NOT localised, because they
// are the law that actually applies to this service. The competent supervisory authority stays the
// German (Hessian) one from OPERATOR — no CNIL substitution.
// Register: formal "vous".
//
// WHY `s6p` IS A GETTER AND NOT A PLAIN VALUE:
// legal.jsx imports ./legal-locales/index.js, which imports this file, which needs OPERATOR back
// from legal.jsx — a module cycle. This file's body runs BEFORE legal.jsx's body, so reading
// `OPERATOR.name` while building the JSX at module scope would hit the const's temporal dead zone
// and throw at import time (a white screen, not a build error). A getter defers the read to render,
// by which point legal.jsx has finished evaluating. The VALUE is still the same JSX element, so the
// shape matches `en` exactly. Do not "simplify" this back into a plain property, and do not copy the
// address in here — OPERATOR is the one place the legal identity lives.
import { OPERATOR } from "../legal.jsx";

// ---------------------------------------------------------------- the Art.13 notice (Assess screen)
export const NOTICE = {
  title: "🇪🇺 Traitement des données",
  p1: (<>En cliquant sur <strong>Assess</strong>, vous lancez une analyse sur un serveur du centre de
       données de <strong>Francfort-sur-le-Main (DE)</strong>. Nous traitons votre adresse e-mail,
       votre adresse IP, les horodatages et l'entreprise demandée — afin de fournir le service et de
       détecter les attaques (Art. 6(1)(b) et 6(1)(f) RGPD). Les journaux de sécurité sont supprimés
       automatiquement au bout de <strong>30 jours</strong>.</>),
  p2: (<><strong>Vos données restent dans l'UE.</strong> Seule exception : votre adresse e-mail est
       transmise à l'API Gmail afin que nous puissions vous envoyer le code à usage unique (Google,
       EU-US Data Privacy Framework). L'analyse elle-même n'utilise que des sources publiques et ne
       reçoit <strong>aucune</strong> donnée d'utilisateur — uniquement le nom de l'entreprise
       évaluée.</>),
  link: "Politique de confidentialité", ok: "Compris — ne plus afficher",
  mini: (<>🇪🇺 Vos données restent dans l'UE (Francfort/FRA1) · e-mail, IP, horodatages &amp; nom de
         l'entreprise sont traités pour fournir le service et détecter les attaques
         (Art. 6(1)(b)/(f) RGPD), journaux conservés 30 jours. </>),
};

// ---------------------------------------------------------------- the /impressum page
export const IMPRESSUM = {
  h1: "Mentions légales (Impressum)", sub: "Informations conformément au § 5 DDG (loi allemande sur les services numériques)",
  s1: "Fournisseur du service",
  s2: "Contact",
  s3: "Responsable du contenu au sens du § 18(2) MStV",
  s4: "Numéro d'identification à la TVA",
  s5: "Règlement des litiges",
  s5p: (<>La Commission européenne met à disposition une plateforme de règlement en ligne des litiges
        (RLL) :{" "}
        <a href="https://ec.europa.eu/consumers/odr/" target="_blank" rel="noreferrer">ec.europa.eu/consumers/odr</a>.
        Nous ne sommes ni disposés ni tenus de participer à une procédure de règlement des litiges
        devant un organisme de médiation de la consommation.</>),
  s6: "Responsabilité pour les contenus et les liens",
  s6p: (<>En tant que fournisseur de services, nous sommes responsables de nos propres contenus sur
        ces pages conformément au droit commun (§ 7(1) DDG). La responsabilité du contenu des pages
        externes liées incombe toujours à leur fournisseur respectif ; aucune infraction n'était
        identifiable au moment de la mise en place du lien. Dès que nous avons connaissance d'une
        violation du droit, nous supprimons immédiatement les liens concernés.</>),
  s7: "Droit d'auteur",
  s7p: (<>Les contenus et œuvres créés par l'exploitant sur ces pages sont soumis au droit d'auteur
        allemand. Les documents d'analyse produits par cybergod.ai constituent du matériel commercial
        interne et ne sont pas destinés à une diffusion publique.</>),
  note: "Remarque : cybergod.ai est un outil interne à accès restreint destiné à l'analyse cyber en avant-vente ; il n'est pas ouvert à l'utilisation par le public.",
  todo: "⚠ Ces mentions légales sont incomplètes. Le nom, l'adresse postale et le numéro de téléphone doivent être renseignés dans OPERATOR (src/legal.jsx) avant publication — en Allemagne, un Impressum incomplet est juridiquement attaquable.",
};

// ---------------------------------------------------------------- the /contact page
export const CONTACT = {
  h1: "Contact", sub: "Une ligne directe — sans formulaire, sans file d'attente",
  lead: "Des questions sur l'accès, sur une analyse, sur la protection des données ou sur un partenariat ? Écrivez-nous directement.",
  email: "E-mail", emailD: "Pour l'accès, les demandes relatives à la protection des données et toute question commerciale. Réponse en général le jour ouvré même.",
  li: "LinkedIn", liD: "La voie la plus rapide pour une prise de contact professionnelle.",
  wa: "WhatsApp", waD: "La voie la plus rapide. Directement sur le téléphone, réponse généralement en quelques minutes.",
  tg: "Telegram", tgD: "Message direct — la plateforme sur laquelle tournent également les bots d'assessment.",
  gh: "GitHub", ghD: "Parcours technique et projets.",
  access: "Demander un accès",
  accessD: "cybergod.ai est à accès restreint : une adresse e-mail partenaire approuvée est requise. Indiquez dans votre message votre société et l'adresse à activer.",
  legal: "Mentions légales : ", soon: "canal à venir",
};

// ---------------------------------------------------------------- the /privacy page
export const PRIVACY = {
  h1: "Confidentialité et traitement des données", sub: "Datenschutz & Datenverarbeitung — cybergod.ai",
  lead: "La version allemande de la présente politique constitue le texte juridiquement contraignant ; cette traduction française est fournie uniquement pour en faciliter la lecture. cybergod.ai est un outil interne d'analyse cyber en avant-vente. Cette page explique quelles données nous traitons, sur quelle base légale, où elles sont conservées et pendant combien de temps nous les conservons — conformément aux Art. 13/14 RGPD.",
  s1: "1. Où se trouvent vos données",
  s1p: (<><strong>Vos données à caractère personnel restent dans l'UE.</strong> L'application, la base
       de données, les sessions, les documents générés et les journaux de sécurité s'exécutent tous
       sur un serveur unique situé dans le{" "}
       <strong>centre de données de Francfort-sur-le-Main, Allemagne (DigitalOcean, région
       FRA1)</strong>. Il n'existe aucune réplication ni aucune sauvegarde en dehors de l'UE.</>),
  s1sub: "Sous-traitants (Art. 28 RGPD) :",
  s1list: [
    (<><strong>DigitalOcean</strong> — hébergement du serveur, région de Francfort (FRA1), UE.</>),
    (<><strong>Google (API Gmail)</strong> — remet le code à usage unique (OTP) à votre adresse e-mail
       et remet à l'exploitant les notifications d'exploitation et de sécurité. Ces notifications
       peuvent contenir des <strong>métadonnées techniques relatives à une visite (adresse IP, pays,
       navigateur/appareil, page demandée)</strong>, afin que l'exploitant puisse examiner les accès
       et les événements de sécurité (Art. 6(1)(f) RGPD). Google est certifiée au titre de l'EU-US
       Data Privacy Framework (Art. 45 RGPD). Aucun contenu d'analyse n'est transmis.</>),
    (<><strong>Telegram</strong> — uniquement si vous utilisez l'accès facultatif par Telegram ; votre
       identifiant d'utilisateur Telegram s'applique alors.</>),
  ],
  s1note: (<>L'analyse elle-même n'exploite que des <strong>données d'infrastructure publiquement
           visibles de l'entreprise évaluée</strong> (Shodan, RIPE, CAIDA, PeeringDB, crt.sh) et
           rédige le texte du rapport via un point de terminaison d'IA. Ces services ne reçoivent{" "}
           <strong>que le nom de l'entreprise ou le domaine/ASN de la cible</strong>, ou le constat
           technique — <strong>aucun identifiant d'utilisateur, aucune adresse e-mail, aucune adresse
           IP d'utilisateur</strong>. Ils ne sont donc pas destinataires de vos données à caractère
           personnel.</>),
  s2: "2. Ce que nous traitons",
  th: ["Données", "Finalité", "Base légale", "Conservation"],
  rows: [
    ["Adresse e-mail (connexion, OTP)", "Contrôle d'accès, authentification à deux facteurs",
     "Art. 6(1)(b) — contrat/utilisation ; Art. 6(1)(f) — sécurité", "Pendant toute la durée de l'accès"],
    ["Adresse IP, horodatage, user-agent, appareil/navigateur, pays",
     "Détection des attaques (DDoS, force brute, scanners), prévention des abus, exploitation",
     "Art. 6(1)(f) — intérêt légitime à la sécurité informatique (considérant 49)",
     "30 jours (conservation des journaux), puis suppression automatique"],
    ["Entreprises demandées, langue, heure, documents générés",
     "Fourniture de l'analyse, imputation des coûts, traçabilité",
     "Art. 6(1)(b), Art. 6(1)(f)", "90 jours, ou jusqu'à suppression par l'utilisateur"],
    ["Alertes de sécurité (règle, objet, éléments forensiques)", "Réponse aux incidents", "Art. 6(1)(f)", "30 jours"],
  ],
  s2note: (<><strong>Aucun</strong> cookie publicitaire, <strong>aucun</strong> suivi inter-sites,
           <strong> aucun</strong> profilage, <strong>aucune</strong> décision automatisée produisant
           des effets juridiques (Art. 22). Le seul cookie déposé est un cookie de session strictement
           nécessaire (§ 25(2)(2) TDDDG — sans consentement requis).</>),
  s3: "3. Minimisation des données (Art. 5(1)(c))",
  s3list: [
    (<>Géolocalisation <strong>au niveau du pays uniquement</strong> — ni ville, ni coordonnées. Base
       de données locale hors ligne, aucune interrogation de tiers.</>),
    (<>Les fichiers statiques (CSS/images) ne sont pas journalisés.</>),
    (<>Les adresses IP peuvent être conservées sous forme <strong>hachée</strong> par l'exploitant
       (<code>TELEMETRY_HASH_IPS=1</code>) : la corrélation est préservée, l'identifiant ne l'est
       pas.</>),
    (<>Les cibles des analyses sont des <strong>entreprises</strong>, et non des personnes physiques.
       Seules des données d'infrastructure publiquement visibles sont exploitées — <strong>aucun
       balayage actif</strong> n'est effectué.</>),
  ],
  s4: "4. Vos droits (Art. 15–21 RGPD)",
  s4p: (<>Accès, rectification, effacement, limitation, portabilité, ainsi que le{" "}
        <strong>droit d'opposition au traitement fondé sur l'intérêt légitime</strong>. Demandes à{" "}
        <a href="mailto:feranicus@s4biz.io">feranicus@s4biz.io</a> — réponse dans un délai d'un mois
        (Art. 12(3)). Vous pouvez également introduire une réclamation auprès d'une autorité de
        contrôle (Art. 77).</>),
  s5: "5. Sécurité (Art. 32 RGPD)",
  s5list: [
    "Chiffrement TLS de l'ensemble du transport ; renouvellement automatique des certificats.",
    "Accès zero trust : identité inscrite sur liste d'autorisation + mot de passe partagé + code à usage unique envoyé par e-mail.",
    "Les documents sont rattachés à leur propriétaire — seul l'utilisateur qui les a générés peut les lire.",
    "Détection continue des attaques avec alertes (force brute, DDoS, scanners, exfiltration).",
    "Application régulière et automatisée des correctifs de sécurité du serveur.",
  ],
  s6: "6. Responsable du traitement",
  // getter — see the header comment (module cycle: OPERATOR is read at render, not at import).
  get s6p() {
    return (<>Le responsable du traitement au sens du RGPD est <strong>{OPERATOR.name}</strong>,{" "}
           {OPERATOR.street}, {OPERATOR.zipCity}, {OPERATOR.country} —{" "}
           <a href={"mailto:" + OPERATOR.email}>{OPERATOR.email}</a>. Coordonnées complètes dans les{" "}
           <a href="/impressum">mentions légales</a>. Usage interne pour l'avant-vente ; les documents
           générés constituent du matériel commercial interne. Vous avez le droit d'introduire une
           réclamation auprès d'une autorité de contrôle de la protection des données (Art. 77 RGPD) ;
           l'autorité compétente est <strong>{OPERATOR.authority}</strong>.</>);
  },
  credit: "Correspondance IP-pays : ", disclaimerT: "Remarque : ",
  disclaimer: "Ce texte décrit le traitement technique réel. Il ne constitue pas un conseil juridique et devrait être examiné par un délégué à la protection des données avant toute publication externe.",
};
