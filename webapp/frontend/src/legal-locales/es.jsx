// legal-locales/es.jsx — see ./index.js. Missing exports fall back to English, then German.
// German is the NORMATIVE text; this is a reading translation.
//
// SCOPE OF THIS FILE: a reading translation for Spanish (es-ES, peninsular, `usted`). It does not
// create, soften or strengthen a single obligation. Every retention period (30 days / 90 days),
// every legal basis, the single non-EU recipient (Google / Gmail API under the EU-US Data Privacy
// Framework), the FRA1 Frankfurt hosting claim and the DB-IP credit are carried across verbatim.
// DSGVO article numbers become RGPD article numbers; § 5 DDG, § 7(1) DDG, § 18(2) MStV and
// § 25(2)(2) TDDDG are GERMAN statutes and keep their German citation — there is no Spanish
// equivalent that applies here. The competent supervisory authority stays the Hessian one named in
// OPERATOR; it is NOT replaced by the AEPD.
//
// The PRIVACY lead opens by saying the German version is authoritative — that sentence is what makes
// shipping a translated legal page safe.
import { OPERATOR } from "../legal.jsx";

// WHY A COMPONENT AND NOT A PLAIN FRAGMENT: legal.jsx imports ./legal-locales/index.js, which
// imports this file — a module cycle. Reading OPERATOR at MODULE-EVALUATION time (inside a bare
// `(<>...{OPERATOR.name}...</>)`) would hit the temporal dead zone, because this module's body runs
// before legal.jsx's does. Wrapping it in a component defers the read to RENDER time, by which
// point legal.jsx is fully initialised. The rendered output is identical to the `en` variant.
function Controller() {
  return (<>El responsable del tratamiento a efectos del RGPD es <strong>{OPERATOR.name}</strong>,{" "}
          {OPERATOR.street}, {OPERATOR.zipCity}, {OPERATOR.country} —{" "}
          <a href={"mailto:" + OPERATOR.email}>{OPERATOR.email}</a>. Datos completos en el{" "}
          <a href="/impressum">aviso legal</a>. Uso interno para la preventa; los documentos
          generados son material comercial interno. Tiene derecho a presentar una reclamación ante
          una autoridad de control en materia de protección de datos (art. 77 RGPD); la autoridad
          competente es <strong>{OPERATOR.authority}</strong>.</>);
}

// ---------------------------------------------------------------- the Art.13 notice (Assess screen)
export const NOTICE = {
  title: "🇪🇺 Tratamiento de datos",
  p1: (<>Al pulsar <strong>Assess</strong> se inicia un análisis en un servidor del centro de datos
       de <strong>Fráncfort del Meno (DE)</strong>. Tratamos su dirección de correo electrónico, su
       dirección IP, marcas de tiempo y la empresa solicitada — para prestar el servicio y detectar
       ataques (art. 6(1)(b) y 6(1)(f) RGPD). Los registros de seguridad se eliminan automáticamente
       transcurridos <strong>30 días</strong>.</>),
  p2: (<><strong>Sus datos permanecen en la UE.</strong> La única excepción: su dirección de correo
       electrónico se transmite a la API de Gmail para poder enviarle el código de un solo uso
       (Google, EU-US Data Privacy Framework). El análisis en sí utiliza únicamente fuentes públicas
       y no recibe <strong>ningún</strong> dato de usuario — solo el nombre de la empresa
       evaluada.</>),
  link: "Aviso de privacidad", ok: "Entendido — no volver a mostrar",
  mini: (<>🇪🇺 Sus datos permanecen en la UE (Fráncfort/FRA1) · la dirección de correo electrónico,
         la IP, las marcas de tiempo y el nombre de la empresa se tratan para prestar el servicio y
         detectar ataques (art. 6(1)(b)/(f) RGPD); registros conservados 30 días. </>),
};

// ---------------------------------------------------------------- the /impressum page
export const IMPRESSUM = {
  h1: "Aviso legal (Impressum)", sub: "Información conforme al § 5 DDG (Ley alemana de servicios digitales)",
  s1: "Prestador del servicio",
  s2: "Contacto",
  s3: "Responsable del contenido conforme al § 18(2) MStV",
  s4: "Número de identificación a efectos del IVA",
  s5: "Resolución de litigios",
  s5p: (<>La Comisión Europea facilita una plataforma de resolución de litigios en línea (ODR):{" "}
        <a href="https://ec.europa.eu/consumers/odr/" target="_blank" rel="noreferrer">ec.europa.eu/consumers/odr</a>.
        No estamos dispuestos ni obligados a participar en procedimientos de resolución de litigios
        ante una junta de arbitraje de consumo.</>),
  s6: "Responsabilidad por los contenidos y los enlaces",
  s6p: (<>Como prestador de servicios respondemos de los contenidos propios de estas páginas
        conforme a la legislación general (§ 7(1) DDG). Del contenido de las páginas externas
        enlazadas responde siempre su respectivo proveedor; en el momento de establecer el enlace no
        se apreciaron infracciones legales. Retiramos dichos enlaces de inmediato en cuanto tenemos
        conocimiento de una infracción.</>),
  s7: "Derechos de autor",
  s7p: (<>Los contenidos y las obras creados por el operador en estas páginas están sujetos a la
        legislación alemana sobre derechos de autor. Los documentos de análisis generados por
        cybergod.ai son material comercial interno y no están destinados a su difusión pública.</>),
  note: "Nota: cybergod.ai es una herramienta interna de acceso restringido para el análisis de ciberseguridad en preventa; no está abierta al público general.",
  todo: "⚠ Este aviso legal está incompleto. Antes de su publicación deben cumplimentarse el nombre, la dirección postal y el número de teléfono en OPERATOR (src/legal.jsx) — en Alemania, un Impressum incompleto puede dar lugar a requerimientos legales.",
};

// ---------------------------------------------------------------- the /contact page
export const CONTACT = {
  h1: "Contacto", sub: "Una línea directa — sin formularios, sin colas",
  lead: "¿Tiene preguntas sobre el acceso, sobre un análisis, sobre protección de datos o sobre una colaboración? Escríbanos directamente.",
  email: "Correo electrónico", emailD: "Para el acceso, las solicitudes en materia de protección de datos y cualquier asunto comercial. Normalmente se responde el mismo día laborable.",
  li: "LinkedIn", liD: "La vía más rápida para una presentación profesional.",
  wa: "WhatsApp", waD: "La vía más rápida. Directo al móvil, normalmente con respuesta en cuestión de minutos.",
  tg: "Telegram", tgD: "Mensaje directo — la misma plataforma en la que funcionan los bots de análisis.",
  gh: "GitHub", ghD: "Trayectoria técnica y proyectos.",
  access: "Solicitar acceso",
  accessD: "cybergod.ai es de acceso restringido: se requiere una dirección de correo electrónico de socio autorizada. Indique en su mensaje su empresa y la dirección que desea habilitar.",
  legal: "Información legal: ", soon: "canal próximamente",
};

// ---------------------------------------------------------------- the /privacy page
export const PRIVACY = {
  h1: "Privacidad y tratamiento de datos", sub: "Datenschutz & Datenverarbeitung — cybergod.ai",
  lead: "La versión alemana de este texto es la versión auténtica y jurídicamente determinante; esta traducción se ofrece únicamente para facilitar su lectura. cybergod.ai es una herramienta interna para el análisis de ciberseguridad en preventa. Esta página explica qué datos tratamos, sobre qué base jurídica, dónde se almacenan y durante cuánto tiempo los conservamos — conforme a los art. 13/14 RGPD.",
  s1: "1. Dónde se almacenan sus datos",
  s1p: (<><strong>Sus datos personales permanecen en la UE.</strong> La aplicación, la base de datos,
       las sesiones, los documentos generados y los registros de seguridad se ejecutan en un único
       servidor del <strong>centro de datos de Fráncfort del Meno, Alemania (DigitalOcean, región
       FRA1)</strong>. No existe replicación ni copia de seguridad fuera de la UE.</>),
  s1sub: "Encargados del tratamiento (art. 28 RGPD):",
  s1list: [
    (<><strong>DigitalOcean</strong> — alojamiento del servidor, región de Fráncfort (FRA1), UE.</>),
    (<><strong>Google (API de Gmail)</strong> — entrega el código de un solo uso (OTP) a su dirección
       de correo electrónico y remite al operador las notificaciones de funcionamiento y de
       seguridad. Dichas notificaciones pueden contener <strong>metadatos técnicos de un acceso
       (dirección IP, país, navegador/dispositivo, página solicitada)</strong> para que el operador
       pueda revisar los accesos y los incidentes de seguridad (art. 6(1)(f) RGPD). Google está
       certificada conforme al EU-US Data Privacy Framework (art. 45 RGPD). No se transmite ningún
       contenido de los análisis.</>),
    (<><strong>Telegram</strong> — únicamente si utiliza el acceso opcional por Telegram; en tal caso
       se aplica su identificador de usuario de Telegram.</>),
  ],
  s1note: (<>El análisis en sí evalúa exclusivamente <strong>datos de infraestructura visibles
           públicamente de la empresa evaluada</strong> (Shodan, RIPE, CAIDA, PeeringDB, crt.sh) y
           redacta el texto del informe a través de un servicio (endpoint) de IA. Esos servicios
           reciben{" "}
           <strong>únicamente el nombre de la empresa o el dominio/ASN del objetivo</strong>, o bien
           el hallazgo técnico — <strong>ningún identificador de usuario, ninguna dirección de correo
           electrónico, ninguna dirección IP de un usuario</strong>. Por tanto, no son destinatarios
           de sus datos personales.</>),
  s2: "2. Qué datos tratamos",
  th: ["Datos", "Finalidad", "Base jurídica", "Conservación"],
  rows: [
    ["Dirección de correo electrónico (inicio de sesión, OTP)", "Control de acceso, autenticación de dos factores",
     "Art. 6(1)(b) — contrato/uso; art. 6(1)(f) — seguridad", "Mientras exista el acceso"],
    ["Dirección IP, marca de tiempo, agente de usuario, dispositivo/navegador, país",
     "Detección de ataques (DDoS, fuerza bruta, escáneres), prevención de abusos, explotación del servicio",
     "Art. 6(1)(f) — interés legítimo en la seguridad informática (considerando 49)",
     "30 días (conservación de registros); después se eliminan automáticamente"],
    ["Empresas solicitadas, idioma, momento, documentos generados",
     "Prestación del análisis, imputación de costes, trazabilidad",
     "Art. 6(1)(b), art. 6(1)(f)", "90 días, o hasta que el usuario los elimine"],
    ["Alertas de seguridad (regla, asunto, datos forenses)", "Respuesta a incidentes", "Art. 6(1)(f)", "30 días"],
  ],
  s2note: (<><strong>Sin</strong> cookies publicitarias, <strong>sin</strong> seguimiento entre
           sitios, <strong>sin</strong> elaboración de perfiles, <strong>sin</strong> decisiones
           automatizadas con efectos jurídicos (art. 22). La única cookie que se instala es una
           cookie de sesión técnicamente necesaria (§ 25(2)(2) TDDDG — no requiere
           consentimiento).</>),
  s3: "3. Minimización de datos (art. 5(1)(c))",
  s3list: [
    (<>Geolocalización <strong>únicamente a nivel de país</strong> — sin ciudad ni coordenadas. Base
       de datos local sin conexión, sin consultas a terceros.</>),
    (<>Los archivos estáticos (CSS/imágenes) no se registran.</>),
    (<>El operador puede almacenar las direcciones IP <strong>con hash</strong>{" "}
       (<code>TELEMETRY_HASH_IPS=1</code>): se conserva la correlación, pero no el identificador.</>),
    (<>Los objetivos de los análisis son <strong>empresas</strong>, no personas físicas. Solo se
       evalúan datos de infraestructura visibles públicamente — <strong>no se realiza ningún escaneo
       activo</strong>.</>),
  ],
  s4: "4. Sus derechos (art. 15–21 RGPD)",
  s4p: (<>Acceso, rectificación, supresión, limitación, portabilidad y el{" "}
        <strong>derecho a oponerse al tratamiento basado en intereses legítimos</strong>. Dirija sus
        solicitudes a <a href="mailto:feranicus@s4biz.io">feranicus@s4biz.io</a> — respuesta en el
        plazo de un mes (art. 12(3)). También puede presentar una reclamación ante una autoridad de
        control (art. 77).</>),
  s5: "5. Seguridad (art. 32 RGPD)",
  s5list: [
    "Cifrado TLS en todo el transporte; renovación automática de los certificados.",
    "Acceso de confianza cero: identidad en lista de permitidos + contraseña compartida + código de un solo uso enviado por correo electrónico.",
    "Los documentos están vinculados a su propietario — solo puede leerlos el usuario que los generó.",
    "Detección continua de ataques con alertas (fuerza bruta, DDoS, escáneres, exfiltración).",
    "Aplicación periódica y automatizada de parches de seguridad en el servidor.",
  ],
  s6: "6. Responsable del tratamiento",
  s6p: (<Controller />),
  credit: "Asignación de IP a país: ", disclaimerT: "Nota: ",
  disclaimer: "Este texto describe el tratamiento técnico real. No constituye asesoramiento jurídico y debería ser revisado por un delegado o una delegada de protección de datos antes de su publicación externa.",
};
