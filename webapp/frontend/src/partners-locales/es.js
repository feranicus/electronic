// partners-locales/es.js: la traducción al español del contenido de /partners.
//
// en.js es la REFERENCIA. Este fichero solo traduce el texto: la forma del objeto (los mismos
// nombres exportados, los mismos identificadores de sección en el mismo orden, el mismo número de
// columnas y de viñetas) la comprueba tools/partners_gate.mjs y una divergencia rompe la build.
//
// NO SE TRADUCEN los valores estructurales: `id`, `group`, `accent`, la `k` de `change.cells`
// (new / closed / open) y `arts[].n`. Son claves de búsqueda; traducir una clave hace que el
// contenido desaparezca en silencio.

export const meta = {
  docTitle: "Para quién es",
  kicker: "Un nombre. Cuatro documentos listos para el consejo. Once públicos.",
  h1a: "Escriba el nombre de una empresa.",
  h1b: "Obtenga el ",
  h1c: "panorama completo del riesgo",
  h1d: " en minutos.",
  lede:
    "No se envía ni un solo paquete a la empresa evaluada. Todo se construye a partir de fuentes " +
    "que cualquier investigador puede consultar de forma lícita. Por eso no hay nada que instalar, " +
    "no hay que pedir permiso a nadie y no hay que esperar ningún cuestionario. Siempre se " +
    "obtienen cuatro documentos.",
  artsNote:
    "Existe además un quinto documento: un informe web autónomo que reúne los cuatro anteriores y " +
    "se abre en cualquier navegador. Es el que la gente reenvía dentro de su organización. Todos " +
    "los documentos están disponibles en inglés, alemán o ruso.",
  railTitle: "Para quién es",
  groupPartners: "Socios",
  groupBuyers: "Compradores",
  groupEngage: "Cómo colaborar",
  foot:
    "El contenido procede del material informativo para socios y reguladores y del paquete legal " +
    "firmado. Por decisión expresa, en ninguna parte figuran precios, descuentos, recuentos de " +
    "puestos ni compromisos. Los volúmenes de reuniones de los socios son los que ellos mismos " +
    "comunican y dependen de cada comercial. El resultado de la evaluación no constituye " +
    "asesoramiento jurídico. Se han eliminado todas las referencias a clientes identificados.",
};

export const arts = [
  { n: "1", name: "Hallazgos", body:
    "Toda la exposición hacia internet, clasificada de Crítica a Baja. Cada hallazgo indica qué " +
    "es, por qué importa, cómo corregirlo y la dirección y el puerto exactos en los que se observó." },
  { n: "2", name: "El riesgo en dinero", body:
    "Los mismos hallazgos expresados en dinero, con el método reconocido Factor Analysis of " +
    "Information Risk. Coste de un incidente, peor caso anual y una curva que desciende a medida " +
    "que se cierran los hallazgos. Escrito para el director financiero." },
  { n: "3", name: "Actores de amenaza", body:
    "Qué atacantes son realmente relevantes para este sector y estos países, y cómo operan. La " +
    "respuesta cuando el consejo pregunta quién vendría a por nosotros." },
  { n: "4", name: "Cumplimiento normativo", body:
    "Los hallazgos vinculados a los artículos de las leyes que aplican allí donde opera la " +
    "empresa, con los plazos reales. Hoy, Unión Europea y Canadá." },
];

export const sections = [
  // ------------------------------------------------- PROVEEDORES DE SERVICIOS GESTIONADOS
  {
    id: "msp", group: "partners", nav: "Proveedores de servicios gestionados",
    eyebrow: "Socio", h2: "Para proveedores de servicios gestionados",
    scr: {
      s: "Usted gestiona la seguridad de muchos clientes a la vez, con un equipo que no puede crecer al ritmo de su cartera.",
      c: "Revisar a mano la exposición de un solo cliente cuesta cerca de una jornada de analista. A escala eso no ocurre, así que la revisión trimestral de negocio acaba siendo un informe de situación al que nadie asigna presupuesto.",
      a: "Evalúe a todos los clientes de su cartera con la misma periodicidad, a un coste que no aumenta con el número de clientes. Y venda después la solución en cuatro niveles distintos.",
    },
    cols: [
      { h: "1. Qué vende usted", li: [
        "La propia evaluación, facturada, bajo su marca.",
        "Una repetición mensual o trimestral con un informe de lo que ha cambiado. Ese informe es el servicio gestionado.",
        "Licencias, vendidas en paquetes o en modalidad ilimitada, con las que gana margen por sí mismas.",
      ] },
      { h: "2. Por qué los números cuadran", li: [
        "Un solo analista cubre toda su cartera en lugar de una única cuenta.",
        "Dar de alta a un cliente no le exige nada a él: ningún software que instalar, ningún acceso, ningún formulario.",
        "El documento de cumplimiento responde al auditor en la misma ejecución, de modo que no hay un segundo proyecto al que asignar personal.",
      ] },
      { h: "3. Dónde está el margen", li: [
        "No en el informe. Está en las cuatro vías para cerrar un hallazgo, que se detallan más abajo.",
        "Sus gestores de cuenta ganan un motivo para llamar a cada cliente, todos los meses, con algo nuevo que contar.",
        "Un hallazgo cerrado demuestra que el contrato de mantenimiento funciona, y eso es lo más difícil de demostrar en seguridad.",
      ] },
    ],
    ladder: { h: "Las cuatro vías para cerrar un hallazgo, de la más económica a la más cara", items: [
      { b: "Asesoramiento.", t: "Un taller que recorre cada hallazgo frente a lo que el cliente ya tiene." },
      { b: "Sin gasto nuevo, con su propio equipamiento.", t: "La mayoría de los hallazgos se cierran mediante cambios de configuración, de ubicación y de proceso en productos que ya están pagando. Usted entrega una lista de acciones, cada una asociada a la herramienta que la resuelve." },
      { b: "Código abierto.", t: "Cuando el equipamiento existente no puede cerrar la brecha, un diseño basado en código abierto en lugar de una compra. No hay licencia que adquirir. El coste se traslada al conocimiento y a la operación, que el cliente o bien contrata en plantilla o bien le compra a usted." },
      { b: "Un producto comercial.", t: "Solo cuando ninguna de las opciones anteriores funciona. La selección se mantiene dentro de la lista de proveedores homologados del cliente. Usted asesora sobre encaje, secuencia e integración." },
    ] },
    win: { h: "La propuesta, dicha sin rodeos", p:
      "Un informe aislado es un proyecto. Un informe mensual de lo que ha cambiado es una " +
      "suscripción. Usted vende el hallazgo y el camino para corregirlo, en cuatro niveles, a un " +
      "cliente que ya confía en usted." },
    steps: [
      { k: "Semana 1", v: "Ejecute sus diez cuentas más grandes y lea lo que devuelve." },
      { k: "Semana 2", v: "Envíe un solo hallazgo a cada una. Vea el método más abajo." },
      { k: "Semana 3", v: "Ponga su marca y añádalo a su nivel de servicio gestionado." },
    ],
    cta: { btn: "Hable con nosotros", txt: "Los paquetes de licencias, los planes ilimitados, los niveles y las condiciones son materia comercial. Consúltenos." },
  },

  // ------------------------------------------------------------------------- DISTRIBUIDORES
  {
    id: "var", group: "partners", nav: "Distribuidores",
    eyebrow: "Socio", h2: "Para distribuidores",
    scr: {
      s: "Usted vende tecnología y gana por la relación, por el momento oportuno y por la calidad de la conversación que es capaz de abrir.",
      c: "La primera reunión técnica es lo más difícil de conseguir. El sustituto habitual es un descuento, que le cuesta margen y enseña al cliente a esperar al siguiente.",
      a: "Entre sabiendo ya qué está expuesto en su perímetro. Cobre la evaluación como corresponde y descuente después su importe del trabajo que ella misma destape.",
    },
    cols: [
      { h: "1. Cómo se factura", li: [
        "La evaluación es un servicio de pago y de alcance cerrado. No es un regalo.",
        "Su importe se descuenta después del asesoramiento o de la remediación que venga a continuación.",
        "El cliente, por tanto, no arriesga nada, y usted cobra en cualquier caso.",
      ] },
      { h: "2. En qué más gana usted", li: [
        "Licencias, en paquetes o en modalidad ilimitada, como segunda línea de ingresos recurrente.",
        "Las cuatro vías para cerrar un hallazgo: asesoramiento, su propio equipamiento, código abierto o un producto homologado.",
        "Ejecuciones repetidas, que muestran lo que ha cambiado y reabren la conversación con una periodicidad fija.",
      ] },
      { h: "3. Qué gana su equipo comercial", li: [
        "Un motivo para llamar a quien sea, con algo concreto que decir.",
        "Clientes nuevos: no necesita permiso ni acceso, así que puede hacer el trabajo antes de que le inviten.",
        "Defensa de la renovación: ejecútelo antes de la fecha de renovación de un competidor y enseñe lo que ha cambiado.",
      ] },
    ],
    win: { h: "La propuesta, dicha sin rodeos", p:
      "Un descuento compra una operación. Saber más que ellos sobre su propio perímetro compra la " +
      "relación, y esta vez le pagan por el trabajo que le abrió la puerta." },
    steps: [
      { k: "Día 1", v: "Elija cinco clientes potenciales con los que no consigue reunirse." },
      { k: "Día 2", v: "Envíe un solo hallazgo a cada uno. Nunca el informe." },
      { k: "Día 5", v: "Acuda a la reunión. Ponga precio a la evaluación. Descuéntela del trabajo posterior." },
    ],
    cta: { btn: "Hable con nosotros", txt: "Existen las modalidades de prescripción, reventa, licencia y marca blanca. Condiciones a petición." },
  },

  // ----------------------------------------------------------------------------- EL MÉTODO
  {
    id: "play", group: "partners", nav: "El método de apertura", accent: "gold",
    eyebrow: "Todos los socios lo usan", h2: "Envíe un solo hallazgo. Reserve el informe.",
    scr: {
      s: "Ya ha ejecutado la evaluación y tiene en la mano un documento con todo dentro.",
      c: "Un cliente potencial que no pidió un informe lo lee como material de venta y lo aparta. Además, un informe completo exige un hueco de agenda que nadie tiene este trimestre.",
      a: "Envíe exactamente un hallazgo, con su evidencia y con la forma de corregirlo. Ese único hallazgo es lo que le consigue la reunión. El informe es lo que vende dentro de ella.",
    },
    quote: {
      q: "Esta dirección no aparece por ningún lado en nuestro inventario de activos.",
      by: "Un ingeniero de seguridad de red de una gran empresa regulada, viendo una ejecución en " +
          "directo. La plataforma había sacado a la luz una dirección atribuida a su propia " +
          "organización. No fue capaz de encontrarla en el inventario interno de activos. Empresa, " +
          "sector y detalles omitidos.",
    },
    cols: [
      { h: "Cómo aplicarlo", li: [
        "Ejecute la evaluación, lea los hallazgos y elija exactamente uno.",
        "Envíe ese hallazgo, con la evidencia y la recomendación para corregirlo.",
        "No adjunte el informe. Elimine los detalles identificativos si el contacto es en frío.",
        "Pida treinta minutos para repasar el resto.",
      ] },
      { h: "Por qué un hallazgo gana al informe", li: [
        "**Un activo desconocido es el hallazgo más potente que existe.** Una dirección que está fuera del inventario está fuera del parcheo, del escaneo y del reporte, y el inventario de activos es la base de todas las normas de seguridad frente a las que se les audita.",
        "**Resiste el escepticismo.** Ante un hallazgo conocido siempre cabe un \"de eso se encarga otro equipo\". Una dirección de la que nadie puede dar cuenta no se responde así.",
        "**Encaja con quien tiene delante.** Aterriza en el equipo con el que ya está hablando, no en un departamento que nadie de la reunión controla.",
        "**Se justifica solo.** Un único servidor sin gestionar expuesto a internet es barato de discutir y caro de ignorar.",
      ] },
    ],
    win: { h: "Lo que cuentan los socios", p:
      "Los socios de Alemania y Suiza que aplican este método comunican de seis a diez primeras " +
      "reuniones nuevas por comercial y semana. Es evidente que depende de la capacidad de cada " +
      "comercial para convertir un dato en una conversación, así que preferimos que se lo cuenten " +
      "ellos mismos. Nosotros organizamos la llamada." },
    cta: { btn: "Solicite una llamada de referencia", ghost: true, txt: "Hay socios de referencia disponibles en el mercado de habla alemana." },
  },

  // --------------------------------------------------------------- INTEGRADORES DE SISTEMAS
  {
    id: "gsi", group: "partners", nav: "Integradores de sistemas",
    eyebrow: "Socio", h2: "Para integradores de sistemas",
    scr: {
      s: "El descubrimiento es la primera fase de todo programa de seguridad y de transformación que usted ejecuta.",
      c: "Se factura a tarifa de consultoría, se hace a mano, cambia en cada proyecto y es la factura que los clientes discuten. Y sin embargo, nada de lo que viene después es válido sin él.",
      a: "Convierta el descubrimiento en un paso fijo, rápido e idéntico en cada proyecto, para que su margen se desplace a la arquitectura y la remediación, que es donde debe estar.",
    },
    cols: [
      { h: "1. Dónde encaja en su metodología", li: [
        "El descubrimiento pasa a ser una entrada de su metodología, no un sustituto de ella.",
        "Una línea base al inicio del programa y una repetición en cada hito de control.",
        "El avance se demuestra con lo que se ha cerrado, en lugar de afirmarse en un informe de situación.",
      ] },
      { h: "2. Dónde más se aplica", li: [
        "Evaluar a un proveedor sin esperar a que el proveedor colabore.",
        "Dimensionar una empresa recién adquirida antes de conectar su red con la de la matriz.",
        "Cualquier país o filial donde no tenga equipo local.",
      ] },
      { h: "3. Qué cambia en lo comercial", li: [
        "Deja de vender semanas de recopilación de datos y empieza a vender el resultado que esa fase bloqueaba.",
        "El documento económico pone precio al programa en el lenguaje del director financiero desde el primer día.",
        "Cada hallazgo lleva su evidencia, de modo que supera la revisión técnica del propio cliente.",
      ] },
    ],
    win: { h: "La propuesta, dicha sin rodeos", p:
      "La primera factura deja de ser la que su cliente discute, porque ahora compra una respuesta " +
      "en lugar de una actividad." },
    steps: [
      { k: "Paso 1", v: "Ejecútelo en un proyecto en curso y compárelo con lo que su equipo encontró a mano." },
      { k: "Paso 2", v: "Incorpórelo a su entregable estándar de descubrimiento." },
      { k: "Paso 3", v: "Póngale su marca o intégrelo. Vea los dos modelos al final." },
    ],
    cta: { btn: "Hable con nosotros", txt: "Las condiciones por volumen, por región y de integración son materia comercial. Consúltenos." },
  },

  // ------------------------------------------------------------------------------ FABRICANTES
  {
    id: "vendors", group: "partners", nav: "Fabricantes de ciberseguridad",
    eyebrow: "Socio", h2: "Para fabricantes de ciberseguridad",
    scr: {
      s: "Tiene un producto que resuelve un problema real y una demostración que lo enseña funcionando.",
      c: "Su demostración prueba que el producto funciona en general. No prueba que este cliente tenga el problema hoy, así que la evaluación degenera en una comparativa de funcionalidades frente a un competidor.",
      a: "Enseñe al cliente potencial qué tiene abierto en su propio perímetro antes de enseñarle su producto. Después vuelva a ejecutarlo tras el despliegue y demuestre, en dinero, lo que su producto ha cerrado.",
    },
    cols: [
      { h: "1. En su propio equipo comercial", li: [
        "Cada gestor de cuenta lleva consigo una imagen de exposición específica de ese cliente.",
        "Abre puertas en empresas que nunca han oído hablar de usted, sin necesidad de ningún acceso.",
        "El documento económico convierte una exposición técnica en una partida presupuestaria.",
      ] },
      { h: "2. Dentro de su producto", li: [
        "La exposición externa pasa a ser una funcionalidad de su plataforma, servida a través de nuestra interfaz de programación.",
        "Su interfaz, su marca y ningún segundo producto que el cliente tenga que evaluar.",
        "Añade una visión de fuera hacia dentro a un producto que mira sobre todo hacia dentro, y esa es una carencia real en la mayoría de las arquitecturas de seguridad.",
      ] },
      { h: "3. Junto a su producto", li: [
        "Ejecútelo antes y después del despliegue. La diferencia es su caso de éxito.",
        "Da a las renovaciones una cifra en lugar de una sensación.",
        "También puede revender licencias junto a sus propios productos.",
      ] },
    ],
    win: { h: "La propuesta, dicha sin rodeos", p:
      "Nadie discute su propia superficie de ataque. Es el camino más corto entre una demostración " +
      "y un presupuesto." },
    steps: [
      { k: "Evaluar", v: "Ejecútelo sobre tres de sus oportunidades abiertas." },
      { k: "Decidir", v: "Herramienta comercial, línea de reventa o funcionalidad de su plataforma." },
      { k: "Integrar", v: "Los hallazgos llegan a su producto a través de la interfaz de programación." },
    ],
    cta: { btn: "Hable con nosotros", txt: "Las condiciones de integración y de licencia dependen del volumen y de la profundidad de la integración. Consúltenos." },
  },

  // -------------------------------------------------------------------------------- CONSULTORÍA
  {
    id: "consulting", group: "partners", nav: "Firmas de consultoría",
    eyebrow: "Socio", h2: "Para firmas de consultoría",
    scr: {
      s: "Usted vende criterio e independencia. Los clientes pagan por el consejo y por el nombre de la portada.",
      c: "La recopilación de datos consume la mayor parte del proyecto y es la parte que los clientes menos quieren pagar. Usted factura perfiles junior por reunir datos y socios por interpretarlos, y solo lo segundo se valora.",
      a: "Comprima la recopilación de datos de semanas a días, ponga su marca en el resultado y venda la interpretación.",
    },
    cols: [
      { h: "1. Qué puede vender", li: [
        "Un primer encargo de pago, entregado en días, que abre el proyecto grande.",
        "Una segunda opinión independiente sobre un programa de seguridad ya en marcha.",
        "Licencias para que el cliente siga usándolo, con las que usted gana margen.",
      ] },
      { h: "2. Qué deja al cliente", li: [
        "Los hallazgos, para el director de seguridad.",
        "El riesgo en dinero, para el director financiero.",
        "Los actores de amenaza, para el consejo, y el cumplimiento normativo, para el comité de auditoría.",
      ] },
      { h: "3. Por qué puede firmarlo con tranquilidad", li: [
        "Cuando no se ha podido consultar una fuente, los hallazgos dicen \"desconocido\" en lugar de inventarse una debilidad.",
        "Cada hallazgo lleva la evidencia en la que se apoya y la fecha en que se observó.",
        "Es repetible, así que el proyecto de continuidad parte de un punto de partida medido.",
      ] },
    ],
    win: { h: "La propuesta, dicha sin rodeos", p:
      "Su nombre va en el documento. Precisamente por eso, un método que se niega a suponer vale " +
      "más para usted que otro que siempre produce una cifra." },
    steps: [
      { k: "Piloto", v: "Un cliente, una ejecución y su propio análisis por encima." },
      { k: "Paquete", v: "Una oferta con nombre propio, alcance cerrado y precio cerrado." },
      { k: "Marca", v: "Su identidad en la plataforma y en todos los documentos." },
    ],
    cta: { btn: "Hable con nosotros", txt: "Condiciones de marca blanca, de licencia y por volumen a petición." },
  },

  // ------------------------------------------------------------------------------------ TELCO
  {
    id: "telco", group: "partners", nav: "Operadores de telecomunicaciones",
    eyebrow: "Socio", h2: "Para operadores de telecomunicaciones",
    scr: {
      s: "Vende conectividad a miles de clientes empresariales y quiere asociarle seguridad antes de que la conectividad se convierta en puro producto básico.",
      c: "Una práctica de seguridad gestionada exige analistas que no puede contratar, con un margen que el mercado no va a pagar, para una base de clientes demasiado grande como para atenderla uno a uno.",
      a: "Venda un servicio de seguridad cuyo coste no aumenta con el número de clientes, entregado por los gestores de cuenta que ya tiene en plantilla.",
    },
    cols: [
      { h: "1. Qué vende usted", li: [
        "Un servicio de evaluación con su marca: su portal, su factura, su precio.",
        "Licencias como línea recurrente, en paquetes o en modalidad ilimitada.",
        "Una revisión periódica que hace el contrato de conectividad más difícil de cambiar de lo que lo haría el precio por sí solo.",
      ] },
      { h: "2. Cómo llega a la base de clientes", li: [
        "Asócielo en el punto de venta, mientras se firma el pedido de conectividad.",
        "Sin un nuevo modelo de venta: sus gestores de cuenta actuales son el canal.",
        "Alcanza la cola larga de clientes pequeños a los que nunca podrá atender con personas.",
      ] },
      { h: "3. Dónde se ejecuta", li: [
        "En su propio entorno o en una nube nacional cuando la regulación lo exija.",
        "En el país que indique su regulador, incluido el servidor de licencias.",
        "En los idiomas que su mercado lee de verdad.",
      ] },
    ],
    win: { h: "La propuesta, dicha sin rodeos", p:
      "Esta es la infrecuente oferta de seguridad que una base de clientes de su tamaño puede " +
      "consumir de verdad, porque nada en ella exige un analista por cliente." },
    steps: [
      { k: "Demostrar", v: "Ejecútelo sobre una muestra de su propia base." },
      { k: "Marca", v: "Vista la plataforma y todos los documentos con su identidad." },
      { k: "Asociar", v: "Inclúyalo en el formulario de pedido de conectividad." },
    ],
    cta: { btn: "Hable con nosotros", txt: "Condiciones de marca blanca, de integración, de licencia y por volumen a petición." },
  },

  // -------------------------------------------------------------------------------------- PYME
  {
    id: "sme", group: "buyers", nav: "Pequeñas y medianas empresas",
    eyebrow: "Comprador", h2: "Para pequeñas y medianas empresas",
    note:
      "Aquí, pequeña o mediana empresa significa un negocio de aproximadamente diez a doscientos " +
      "cincuenta empleados, donde una sola persona se ocupa de la informática además de otro " +
      "trabajo. Esta página está escrita para esa empresa: el propietario, el director general o " +
      "esa única persona.",
    scr: {
      s: "Le dicen que su empresa tiene que tomarse en serio la ciberseguridad, y usted está de acuerdo.",
      c: "El consejo es comprar una prueba de intrusión, un consultor y un conjunto de políticas. Las tres cosas cuestan más que el riesgo que nadie le ha cuantificado, y ninguna responde a la única pregunta que usted tiene de verdad.",
      a: "Descubra qué puede ver un desconocido de su empresa desde fuera, esta misma semana, sin instalar nada y sin dejar entrar a nadie en su red.",
    },
    cols: [
      { h: "1. Qué recibe", li: [
        "Todo lo suyo que está expuesto a internet, incluido lo que nadie recordaba.",
        "Lo que le costaría si algo saliera mal, en dinero, con el método a la vista.",
        "Qué leyes le aplican y con qué plazos, en lenguaje llano.",
      ] },
      { h: "2. Por qué encaja en una empresa de su tamaño", li: [
        "Nada que instalar. Ningún software, ningún acceso, nadie que visite su oficina.",
        "Usted da el nombre de una empresa. Toda la puesta en marcha es esa.",
        "Vuelva a ejecutarlo cada vez que algo cambie, en lugar de una vez al año cuando se lo pueda permitir.",
      ] },
      { h: "3. Qué puede hacer con ello", li: [
        "Reenviarlo tal cual a un cliente que le está auditando.",
        "Entregarlo a su banco o a su aseguradora sin necesidad de traducción.",
        "Pasárselo a su proveedor informático como una lista de trabajo.",
      ] },
    ],
    channel: {
      b: "Cómo se compra.",
      t: "A través de un socio, no directamente de nosotros. O bien elige a uno de nuestros socios " +
         "certificados de su región, o bien nos presenta a la empresa informática en la que ya " +
         "confía y nosotros la incorporamos. Usted conserva la relación que tiene. Ellos ganan la " +
         "capacidad. La elección es suya.",
    },
    win: { h: "La propuesta, dicha sin rodeos", p:
      "La mayoría de las empresas de su tamaño encuentran al menos una cosa que no sabían que era " +
      "visible desde internet. Encontrarla le cuesta una tarde en lugar de un proyecto." },
    steps: [
      { k: "Ahora", v: "Mire la demostración pública. Documentos reales, empresa inventada." },
      { k: "Después", v: "Pídanos a nosotros, o a su propio proveedor, una ejecución con su nombre." },
      { k: "Más adelante", v: "Corrija lo que importa y vuelva a ejecutarlo para demostrar que está cerrado." },
    ],
    cta: { btn: "Encuentre un socio", txt: "Los precios y las condiciones los pone su socio. Díganos su región y le presentamos a uno, o traiga el suyo." },
  },

  // ---------------------------------------------------------------------------- GRANDES EMPRESAS
  {
    id: "enterprise", group: "buyers", nav: "Grandes empresas",
    eyebrow: "Comprador", h2: "Para grandes empresas",
    scr: {
      s: "Tiene equipos de seguridad, herramientas maduras y un presupuesto real. Cada uno de esos equipos posee una parte del cuadro.",
      c: "Nadie puede decir cómo se ve el grupo entero desde fuera y demostrarlo. Las filiales y las adquisiciones dejan activos que ningún equipo reclama. El riesgo de proveedor se evalúa con un formulario que el propio proveedor rellena sobre sí mismo.",
      a: "Una única visión externa de todo el grupo, valorada en dinero, repetida con una periodicidad fija y con un informe de exactamente qué ha cambiado desde la ejecución anterior.",
    },
    cols: [
      { h: "1. Cobertura que sus herramientas no tienen", li: [
        "El grupo completo, incluidas las filiales y las marcas que no llevan el nombre de la matriz.",
        "Proveedores evaluados del mismo modo, sin acceso y sin cuestionario.",
        "Empresas recién adquiridas, antes de conectar su red con la suya.",
      ] },
      { h: "2. Resultados con la forma de su organización", li: [
        "Los hallazgos, para seguridad de red. El riesgo en dinero, para el director financiero y el comité de riesgos.",
        "Los actores de amenaza, para el consejo. El cumplimiento normativo, para auditoría interna.",
        "Ningún equipo tiene que ponerse de acuerdo con otro para poder usar su propio documento.",
      ] },
      { h: "3. Construido para resistir la impugnación", li: [
        "Cada hallazgo lleva la dirección, el puerto, la evidencia y la fecha.",
        "El alcance es deliberadamente conservador: el servidor de otra empresa en infraestructura compartida nunca se informa como suyo.",
        "Cuando no se ha podido consultar una fuente, informa \"desconocido\" en lugar de deducir una debilidad.",
      ] },
    ],
    change: {
      h: "El informe de cambios, que es la parte que importa",
      lead:
        "Una evaluación aislada le dice dónde está. No puede decirle si algo está mejorando. " +
        "Vuelva a ejecutarla y la plataforma compara las dos ejecuciones e informa solo de lo que se ha movido.",
      cells: [
        { k: "new", t: "Nuevos", b: "no existían la vez anterior",
          before: "Exposiciones que ", after: ": un servicio que alguien publicó, un certificado que caducó, un servidor que llegó con una adquisición." },
        { k: "closed", t: "Cerrados", b: "han desaparecido",
          before: "Hallazgos que ya ", after: ". Esta es la prueba de que un presupuesto de remediación ha producido un resultado, que es lo más difícil de demostrar en seguridad." },
        { k: "open", t: "Siguen abiertos", b: "no se han movido",
          before: "Hallazgos planteados anteriormente que ", after: ", con el tiempo que llevan abiertos. Esta es la lista de escalado, y se escribe sola." },
      ],
      tailBefore: "Su proceso de cumplimiento no quiere un informe. Quiere una respuesta fechada y probada a una sola pregunta: ",
      tailBold: "¿qué ha cambiado y ha corregido alguien lo que planteamos?",
      tailAfter: " Eso es lo que convierte esto en un control en lugar de un proyecto, y es la razón para ejecutarlo con una periodicidad fija en vez de una sola vez.",
    },
    channel: {
      b: "Cómo se compra.",
      t: "A través del canal. O bien elige a uno de nuestros socios certificados, o bien designa al " +
         "integrador de sistemas con el que ya trabaja y nosotros lo incorporamos. Su proceso de " +
         "compras, sus contratos y sus relaciones con proveedores actuales permanecen tal como están.",
    },
    win: { h: "La propuesta, dicha sin rodeos", p:
      "Sus equipos conservan todas las herramientas que tienen. Esto responde a la única pregunta " +
      "a la que ninguna de esas herramientas apunta: qué puede ver el mundo exterior de todo lo " +
      "que usted posee. Y después demuestra, mes tras mes, si eso se está reduciendo." },
    steps: [
      { k: "Demostrar", v: "Una unidad de negocio. Compárela con lo que creía tener." },
      { k: "Ampliar", v: "Añada filiales y sus proveedores más críticos." },
      { k: "Operar", v: "Póngalo con una periodicidad fija y gestione el informe de cambios." },
    ],
    cta: { btn: "Hable con nosotros", txt: "Los acuerdos corporativos, el acceso a la interfaz de programación y la documentación de seguridad se tramitan a través de su socio o del nuestro." },
  },

  // ----------------------------------------------------------------------- DESPACHOS DE ABOGADOS
  {
    id: "law", group: "buyers", nav: "Despachos de abogados",
    eyebrow: "Comprador", h2: "Para despachos de abogados",
    scr: {
      s: "Usted asesora en protección de datos, incidentes cibernéticos, fusiones y adquisiciones y exposición regulatoria.",
      c: "Necesita con frecuencia hechos técnicos sobre una empresa que no tiene autorización para tocar. Probar los sistemas de un tercero sin autorización genera exactamente la responsabilidad que usted existe para evitar.",
      a: "Evidencia técnica obtenida sin hacerle nada a nadie, que es precisamente lo que la hace utilizable en su trabajo.",
    },
    cols: [
      { h: "1. Dónde se aplica", li: [
        "**Diligencia debida en una operación:** el patrimonio externo real de la sociedad objetivo, y su riesgo valorado, antes de firmar el contrato de compraventa.",
        "**Después de un incidente:** una imagen independiente y fechada de lo que era públicamente visible.",
        "**Litigios:** una prueba técnica que otro perito puede reproducir.",
      ] },
      { h: "2. Por qué su uso es lícito", li: [
        "Totalmente pasivo. Ni un solo paquete llega a la empresa evaluada.",
        "No se explota nada y no se inicia sesión en nada.",
        "Se construye únicamente a partir de fuentes que cualquier investigador puede consultar de forma lícita, de modo que no hace falta la autorización de nadie.",
      ] },
      { h: "3. Qué puede poner delante de un cliente", li: [
        "Cada hallazgo con su evidencia y la fecha en que se obtuvo.",
        "Qué normas aplican, con las obligaciones y los plazos citados de los textos originales.",
        "La exposición convertida en un importe que el consejo de su cliente entiende.",
      ] },
    ],
    win: { h: "La propuesta, dicha sin rodeos", p:
      "Produce hechos técnicos con la única propiedad que su trabajo exige: se obtuvieron sin " +
      "hacerle nada a nadie. Eso es lo que los hace utilizables." },
    steps: [
      { k: "Evaluar", v: "Ejecútelo sobre un asunto en el que ya asesora." },
      { k: "Verificar", v: "Contraste la cadena de evidencia con su propio estándar." },
      { k: "Adoptar", v: "Conviértalo en un paso estándar de la diligencia debida en operaciones y del trabajo de incidentes." },
    ],
    cta: { btn: "Hable con nosotros", txt: "Condiciones por asunto o para todo el despacho, a través del canal. El resultado no constituye asesoramiento jurídico y no sustituye a un abogado." },
  },

  // -------------------------------------------------------------------------------- ASEGURADORAS
  {
    id: "insurance", group: "buyers", nav: "Aseguradoras",
    eyebrow: "Comprador", h2: "Para aseguradoras, agentes y corredores",
    scr: {
      s: "Usted suscribe seguros de ciberriesgo y los tarifica a partir de lo que el solicitante le cuenta sobre sí mismo.",
      c: "El cuestionario de propuesta lo rellena el propio solicitante, es optimista y está desactualizado el mismo día en que se firma. En la renovación no puede saber si se corrigió algo de lo que el asegurado prometió corregir. Tras un siniestro no puede acreditar qué era visible.",
      a: "Suscriba lo observable en lugar de lo declarado, en todos los riesgos, a un coste que no aumenta con el número de riesgos.",
    },
    cols: [
      { h: "1. ¿Qué prima debe llevar este riesgo?", li: [
        "Una pérdida esperada y un peor caso anual, producidos con el método reconocido Factor Analysis of Information Risk.",
        "Los cálculos quedan a la vista, así que es una entrada técnica para su decisión de tarificación y no una puntuación salida de una caja negra.",
        "Disponible antes de que el solicitante le haya elegido, porque no necesita su colaboración.",
      ] },
      { h: "2. ¿Qué hay realmente en su patrimonio digital?", li: [
        "Toda la exposición hacia internet, clasificada, con la dirección y el puerto.",
        "Independiente del cuestionario de propuesta, de modo que ambos pueden compararse.",
        "Entregado en minutos, así que cabe dentro de un proceso de cotización.",
      ] },
      { h: "3. ¿Cumplen la normativa?", li: [
        "Su situación frente a las leyes de ciberseguridad que les aplican, con los plazos.",
        "El incumplimiento es a la vez un factor de siniestralidad y una cuestión de cobertura.",
        "Los regímenes de la Unión Europea y de Canadá ya están operativos.",
      ] },
    ],
    ladder: { h: "A lo largo de la vida de la póliza", items: [
      { b: "En la cotización.", t: "Minutos, sin necesidad de colaboración." },
      { b: "En la renovación.", t: "El informe de cambios muestra la remediación, o su ausencia. Tarifique la diferencia." },
      { b: "En toda la cartera.", t: "Vuelva a ejecutar toda la cartera cuando aparezca una nueva vulnerabilidad ampliamente explotada y conozca su exposición acumulada ese mismo día." },
      { b: "En el siniestro.", t: "Un registro fechado de lo que era visible desde el exterior." },
    ] },
    win: { h: "La propuesta, dicha sin rodeos", p:
      "Pasa de suscribir lo que dice el solicitante a suscribir lo que se puede observar, de forma " +
      "consistente, en todos los riesgos. Ese es un argumento sobre el ratio de siniestralidad, no " +
      "sobre tecnología." },
    steps: [
      { k: "Calibrar", v: "Ejecútelo sobre riesgos que ya ha suscrito, incluidos los que produjeron siniestros." },
      { k: "Comparar", v: "Ponga los resultados junto a los cuestionarios de propuesta y mire las diferencias." },
      { k: "Integrar", v: "En el proceso de cotización o en su portal de corredores." },
    ],
    cta: { btn: "Hable con nosotros", txt: "Condiciones de cartera, de interfaz de programación y de integración a petición." },
  },

  // ---------------------------------------------------------------------------------- REGULADORES
  {
    id: "regulator", group: "buyers", nav: "Reguladores",
    eyebrow: "Comprador", h2: "Para reguladores y autoridades de supervisión",
    scr: {
      s: "Usted supervisa un conjunto de entidades bajo un mandato de ciberseguridad o de resiliencia operativa.",
      c: "La ley está escrita y los plazos son reales. Su capacidad técnica no lo es. En la práctica inspecciona un puñado de entidades al año, elegidas sin una base técnica. No puede saber si las que no ha inspeccionado son las que importan.",
      a: "Supervise a todo el conjunto a partir de evidencia pública, sin visitar a nadie, y convierta cada incumplimiento en un expediente preparado que su instructor revisa y firma.",
    },
    cols: [
      { h: "1. Cobertura en lugar de muestreo", li: [
        "Todas las entidades supervisadas, evaluadas con el mismo método el mismo día.",
        "Los resultados son comparables en todo el sector, porque nada se mide de forma distinta.",
        "Repetible con una periodicidad fija, de modo que puede medir hacia dónde va el sector.",
      ] },
      { h: "2. Evidencia que resiste la impugnación", li: [
        "Por entidad: la dirección, el puerto, la evidencia y la fecha en que se observó.",
        "Vinculada al artículo concreto que activa.",
        "Cuando no se puede consultar una fuente, informa \"desconocido\" y no afirma que haya incumplimiento.",
      ] },
      { h: "3. Lícito por construcción", li: [
        "Totalmente pasivo. No se toca ninguna entidad, así que no surge ninguna notificación ni autorización.",
        "Reproducible, de modo que resiste la revisión de los propios peritos de la entidad.",
        "Desplegable dentro de su propio entorno o de un entorno nacional cuando el mandato lo exija.",
      ] },
    ],
    ladder: { h: "El circuito sancionador, ejecutado sobre todo el conjunto", items: [
      { b: "Detectar.", t: "Una situación de incumplimiento en una entidad supervisada, con la dirección, el puerto y la fecha en que se observó." },
      { b: "Vincular.", t: "El artículo concreto que activa, ya sea de la normativa europea o de su propio instrumento nacional." },
      { b: "Corroborar.", t: "Cuatro modelos de inteligencia artificial independientes, de cuatro proveedores distintos, revisan el caso. Dos lo construyen y dos intentan derribarlo. La decisión la toman reglas fijas escritas en código, no los modelos, y un caso que ninguno de ellos puede corroborar nunca sale de la cola." },
      { b: "Redactar.", t: "El expediente probado y la propuesta de resolución sancionadora se preparan automáticamente." },
      { b: "Decidir.", t: "Su instructor revisa y firma. La máquina construye el caso y la autoridad lo emite, que es lo que mantiene cada resolución revisable y recurrible." },
    ] },
    win: { h: "La propuesta, dicha sin rodeos", p:
      "Deja de elegir a quién inspeccionar por su reputación. Empieza a supervisar todo el sector " +
      "por evidencia, sin enviar un inspector a un solo edificio y sin que un solo paquete llegue " +
      "a una entidad supervisada." },
    steps: [
      { k: "Piloto", v: "Un sector, un grupo de entidades. Ordénelas." },
      { k: "Comparar", v: "Contraste esa ordenación con su propio conocimiento supervisor." },
      { k: "Escalar", v: "El conjunto completo, con una periodicidad fija y con la cola sancionadora." },
    ],
    cta: { btn: "Hable con nosotros", txt: "Contratación pública, ubicación del alojamiento y condiciones a petición." },
  },

  // ------------------------------------------------------------------------------- MARCA BLANCA
  {
    id: "whitelabel", group: "engage", nav: "Marca blanca", accent: "purple",
    eyebrow: "Cómo colaborar, modelo uno de dos", h2: "Marca blanca",
    scr: {
      s: "Quiere un servicio de seguridad para vender bajo su propia marca.",
      c: "Construir el motor lleva años. Revender la marca de otro significa que la relación con el cliente es con ellos y no con usted.",
      a: "Su marca por delante, nuestro motor por debajo. Su cliente, su contrato, su precio, y ellos nunca nos ven.",
    },
    cols: [
      { h: "Qué pasa a ser suyo", li: [
        "La marca en todas las pantallas y en los cuatro documentos.",
        "La relación con el cliente, el contrato y la factura.",
        "Su propia política de precios, fijada por usted, para su mercado.",
        "Dónde se ejecuta: su nube, su región o un entorno nacional. El servidor de licencias puede residir en el país o la región que usted requiera.",
      ] },
      { h: "Qué no pasa a ser suyo", li: [
        "El código fuente y la propiedad de la plataforma. Recibe una licencia para usarla y presentarla, no para poseerla.",
        "El derecho a sublicenciar el propio software a un tercero.",
        "El desarrollo del motor y sus garantías de exactitud. Eso se queda con nosotros, y es precisamente aquello en lo que usted confía.",
      ] },
    ],
    win: { h: "Elija esto si", p:
      "Quiere un producto que vender: algo en lo que su cliente inicia sesión y que lleva su " +
      "nombre. Es el modelo adecuado para proveedores de servicios gestionados, operadores de " +
      "telecomunicaciones, firmas de consultoría y distribuidores que están montando una práctica " +
      "de seguridad." },
    steps: [
      { k: "Definir", v: "Marca, región de alojamiento, idiomas y qué módulos." },
      { k: "Construir", v: "Nosotros lo personalizamos y lo desplegamos. Usted lo acepta frente a criterios acordados." },
      { k: "Vender", v: "Bajo su marca y a su precio." },
    ],
    cta: { btn: "Hable con nosotros", txt: "Los compromisos, el alcance de la puesta en marcha y los precios son materia comercial y confidencial. Consúltenos." },
  },

  // ----------------------------------------------------------------------------------- INTEGRADO
  {
    id: "oem", group: "engage", nav: "Integrado (OEM)", accent: "purple",
    eyebrow: "Cómo colaborar, modelo dos de dos", h2: "Integrado, también llamado OEM",
    scr: {
      s: "Ya tiene un producto en el que sus clientes inician sesión todos los días.",
      c: "Vender un producto aparte junto a él genera fricción: otro inicio de sesión, otro contrato, otra cosa que explicar. Además diluye el producto que ha tardado años en construir.",
      a: "Nuestro motor dentro de su producto, de modo que su cliente ve una funcionalidad nueva y no un producto nuevo que evaluar.",
    },
    cols: [
      { h: "Cómo funciona", li: [
        "Usted llama a nuestra interfaz de programación. Los hallazgos, el riesgo valorado, el contexto de actores de amenaza, las calificaciones de cumplimiento y los documentos terminados vuelven como datos.",
        "Los muestra en su propia interfaz y con su propia estructura.",
        "Los hallazgos críticos se envían a su plataforma o a su sistema de monitorización de seguridad en cuanto se producen, así que no hay nada que consultar de forma periódica.",
        "Desplegable en su entorno, en la región que exija su arquitectura o su regulador.",
      ] },
      { h: "Qué le aporta", li: [
        "Una capacidad nueva en un producto existente, sin ningún elemento nuevo que el cliente tenga que aprobar.",
        "Sin un segundo inicio de sesión, sin un segundo contrato y sin una segunda vía de soporte.",
        "Control total de la experiencia, de su lugar en su hoja de ruta y de cómo la tarifica.",
        "Sigue pudiendo revender licencias como línea independiente cuando una cuenta lo requiera.",
      ] },
    ],
    vs: {
      a: { h: "La marca blanca es", bold: "producto", before: "Un ", after: " que parece suyo. Su cliente inicia sesión en algo que lleva su marca. Es lo mejor cuando está montando una práctica de servicios y necesita algo que vender." },
      b: { h: "Lo integrado es", bold: "capacidad", before: "Una ", after: " dentro de su producto. Su cliente ve una funcionalidad nueva, no un producto nuevo. Es lo mejor cuando ya es dueño de la pantalla que su cliente mira y no quiere añadir una segunda." },
    },
    win: { h: "Elija esto si", p:
      "Es usted un fabricante de software o de seguridad, una aseguradora con portal o un negocio " +
      "de plataforma. La prueba es sencilla. Si su cliente ya inicia sesión en algo suyo, elija " +
      "integrado. Si no lo hace, elija marca blanca." },
    steps: [
      { k: "Diseñar", v: "Qué llamadas, qué datos y dónde aparece." },
      { k: "Integrar", v: "Claves con alcance limitado, notificaciones de retorno firmadas y una especificación versionada." },
      { k: "Publicar", v: "Pasa a ser una funcionalidad de su plataforma." },
    ],
    cta: { btn: "Hable con nosotros", txt: "La profundidad de la integración, el volumen y las condiciones son materia comercial. Consúltenos." },
  },

  // -------------------------------------------------------------------------------------- CONTACTO
  {
    id: "contact", group: "engage", nav: "Hable con nosotros",
    eyebrow: "Siguiente paso", h2: "Hable con nosotros",
    note:
      "Los precios, los niveles, los modelos de licencia, los compromisos y las condiciones " +
      "contractuales son materia comercial y se acuerdan directamente. De forma deliberada, no se " +
      "publican aquí.",
    cols: [
      { h: "Qué podemos hacer esta semana", li: [
        "Una ejecución en directo sobre el nombre de empresa que usted elija, para que juzgue el resultado y no el discurso comercial.",
        "Una llamada de referencia con un socio que ya lo vende en el mercado de habla alemana.",
        "El paquete legal: contrato de socio, anexo de marca blanca e integración, acuerdo de confidencialidad, acuerdo de nivel de servicio, condiciones de uso, contrato de tratamiento de datos y una ficha técnica de alojamiento.",
        "La documentación de arquitectura de seguridad que le pedirá su responsable de seguridad o su equipo de compras.",
      ] },
      { h: "Qué le preguntaremos", li: [
        "Cuál de los públicos anteriores es usted. Cambia la respuesta de forma sustancial.",
        "Si quiere revenderlo, ponerle su marca o integrarlo en su propio producto.",
        "Si vende licencias, servicios o ambas cosas.",
        "Dónde tienen que estar ubicados los datos y el servidor de licencias.",
      ] },
    ],
    cta: { btn: "Escríbanos", ghost2: "Vea antes la demostración pública", txt: "Cybergod LLC, parte del S4Biz Group" },
  },
];
