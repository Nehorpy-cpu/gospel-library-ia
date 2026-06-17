import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const code = (name) => readFileSync(join(root, "code_nodes", name), "utf8").trim();

const curatedUrls = [
  {
    source_url: "https://www.churchofjesuschrist.org/study/manual/gospel-topics/faith-in-jesus-christ?lang=spa",
    source_name: "Sitio oficial de la Iglesia",
    content_type: "text/html",
    tags: ["Jesucristo", "Fe", "Temas del Evangelio"]
  },
  {
    source_url: "https://www.churchofjesuschrist.org/study/manual/gospel-topics/atonement-of-jesus-christ?lang=spa",
    source_name: "Sitio oficial de la Iglesia",
    content_type: "text/html",
    tags: ["Jesucristo", "Expiación", "Temas del Evangelio"]
  },
  {
    source_url: "https://www.churchofjesuschrist.org/study/manual/gospel-topics/repentance?lang=spa",
    source_name: "Sitio oficial de la Iglesia",
    content_type: "text/html",
    tags: ["Arrepentimiento", "Expiación", "Temas del Evangelio"]
  },
  {
    source_url: "https://www.churchofjesuschrist.org/study/manual/gospel-topics/restoration-of-the-church-study-guide?lang=spa",
    source_name: "Sitio oficial de la Iglesia",
    content_type: "text/html",
    tags: ["Restauración", "José Smith", "Temas del Evangelio"]
  },
  {
    source_url: "https://www.churchofjesuschrist.org/study/manual/gospel-topics/jesus-christ-study-guide?lang=spa",
    source_name: "Sitio oficial de la Iglesia",
    content_type: "text/html",
    tags: ["Jesucristo", "Fe", "Discipulado"]
  },
  {
    source_url: "https://www.churchofjesuschrist.org/study/general-conference/2024/04/16soares?lang=spa",
    source_name: "Sitio oficial de la Iglesia",
    content_type: "text/html",
    tags: ["Jesucristo", "Convenios", "Conferencia General"]
  },
  {
    source_url: "https://www.churchofjesuschrist.org/study/general-conference/2024/10/57nelson?lang=spa",
    source_name: "Sitio oficial de la Iglesia",
    content_type: "text/html",
    tags: ["Jesucristo", "Templo", "Conferencia General"]
  },
  {
    source_url: "https://www.churchofjesuschrist.org/study/general-conference/2024/10/52wada?lang=spa",
    source_name: "Sitio oficial de la Iglesia",
    content_type: "text/html",
    tags: ["Espíritu Santo", "Escrituras", "Conferencia General"]
  },
  {
    source_url: "https://www.churchofjesuschrist.org/study/general-conference/2024/04/56pace?lang=spa",
    source_name: "Sitio oficial de la Iglesia",
    content_type: "text/html",
    tags: ["Libro de Mormón", "Jesucristo", "Conferencia General"]
  },
  {
    source_url: "https://www.churchofjesuschrist.org/study/general-conference/2024/10/34alvarado?lang=spa",
    source_name: "Sitio oficial de la Iglesia",
    content_type: "text/html",
    tags: ["Arrepentimiento", "Senda de los convenios", "Conferencia General"]
  },
  {
    source_url: "https://speeches.byu.edu/spa/talks/brad-wilcox/su-gracia-es-suficiente/",
    source_name: "BYU Speeches Español",
    content_type: "text/html",
    tags: ["Jesucristo", "Gracia", "Expiación"]
  },
  {
    source_url: "https://speeches.byu.edu/spa/talks/david-a-bednar/en-la-fuerza-del-senor/",
    source_name: "BYU Speeches Español",
    content_type: "text/html",
    tags: ["Jesucristo", "Gracia", "Fortaleza espiritual"]
  },
  {
    source_url: "https://speeches.byu.edu/spa/talks/neill-f-marriott/orientar-nuestra-alma-hacia-cristo/",
    source_name: "BYU Speeches Español",
    content_type: "text/html",
    tags: ["Jesucristo", "Discipulado", "Convenios"]
  },
  {
    source_url: "https://speeches.byu.edu/spa/talks/lloyd-d-newell/no-temas/",
    source_name: "BYU Speeches Español",
    content_type: "text/html",
    tags: ["Fe", "Jesucristo", "Confianza en Dios"]
  },
  {
    source_url: "https://speeches.byu.edu/spa/talks/jeffrey-r-holland/santo-por-la-expiacion-de-cristo-el-senor/",
    source_name: "BYU Speeches Español",
    content_type: "text/html",
    tags: ["Expiación", "Perdón", "Jesucristo"]
  },
  {
    source_url: "https://speeches.byu.edu/spa/talks/dallin-h-oaks/acercarnos-mas-a-jesucristo/",
    source_name: "BYU Speeches Español",
    content_type: "text/html",
    tags: ["Jesucristo", "Fe", "Humildad"]
  },
  {
    source_url: "https://speeches.byu.edu/spa/talks/kevin-w-pearson/la-vida-abundante/",
    source_name: "BYU Speeches Español",
    content_type: "text/html",
    tags: ["Espíritu Santo", "Convenios", "Vida abundante"]
  },
  {
    source_url: "https://discursosud.com/el-amor-puro-de-cristo/",
    source_name: "Discursos SUD",
    content_type: "text/html",
    tags: ["Jesucristo", "Caridad", "Discipulado"]
  },
  {
    source_url: "https://discursosud.com/lecciones-de-la-expiacion/",
    source_name: "Discursos SUD",
    content_type: "text/html",
    tags: ["Expiación", "Jesucristo", "Plan de Salvación"]
  },
  {
    source_url: "https://discursosud.com/el-templo-y-la-expiacion/",
    source_name: "Discursos SUD",
    content_type: "text/html",
    tags: ["Templo", "Expiación", "Convenios"]
  },
  {
    source_url: "https://discursosud.com/la-expiacion-de-jesucristo/",
    source_name: "Discursos SUD",
    content_type: "text/html",
    tags: ["Jesucristo", "Expiación", "Sanación"]
  },
  {
    source_url: "https://discursosud.com/2024/07/22/la-expiacion-ayer-y-hoy/",
    source_name: "Discursos SUD",
    content_type: "text/html",
    tags: ["Expiación", "Jesucristo", "Arrepentimiento"]
  },
  {
    source_url: "https://discursosud.com/2024/06/29/tres-bendiciones-de-la-expiacion-de-jesucristo/",
    source_name: "Discursos SUD",
    content_type: "text/html",
    tags: ["Jesucristo", "Expiación", "Bendiciones"]
  },
  {
    source_url: "https://discursosud.com/doctrina-de-salvacion-tomo-1/9/",
    source_name: "Discursos SUD",
    content_type: "text/html",
    tags: ["Doctrina", "Expiación", "Salvación"]
  },
  {
    source_url: "https://discursosud.com/2024/12/17/celebrando-la-pascua/6/",
    source_name: "Discursos SUD",
    content_type: "text/html",
    tags: ["Jesucristo", "Expiación", "Pascua"]
  }
];

const workflow = {
  name: "Gospel Library IA - Ingesta curada en español v1",
  nodes: [
    {
      parameters: {},
      id: "18fa1e6b-c2d9-4eb3-87dd-84fd4ae5d001",
      name: "Inicio manual - Ingesta curada",
      type: "n8n-nodes-base.manualTrigger",
      typeVersion: 1,
      position: [-1000, 0]
    },
    {
      parameters: {
        assignments: {
          assignments: [
            {
              id: "338403af-ffea-4401-b2ec-403a8ae09002",
              name: "urls",
              type: "array",
              value: `={{ ${JSON.stringify(curatedUrls, null, 2)} }}`
            }
          ]
        },
        options: {}
      },
      id: "e38fa307-e214-40bd-a658-ef00a58d1003",
      name: "URLs curadas en español",
      type: "n8n-nodes-base.set",
      typeVersion: 3.4,
      position: [-780, 0]
    },
    {
      parameters: {
        jsCode: code("00_inicializar_reporte_lote.js")
      },
      id: "ef1f6efe-4a98-4211-b44b-bbde71c3d7c6",
      name: "Inicializar reporte de lote",
      type: "n8n-nodes-base.code",
      typeVersion: 2,
      position: [-560, 180]
    },
    {
      parameters: {
        fieldToSplitOut: "urls",
        options: {}
      },
      id: "7c9c5e30-6bb6-46e0-86e2-e9966a34a004",
      name: "Separar lista de URLs",
      type: "n8n-nodes-base.splitOut",
      typeVersion: 1,
      position: [-560, 0]
    },
    {
      parameters: {
        batchSize: 1,
        options: {}
      },
      id: "fca9e89b-1ab8-43d8-a2bc-6834dadbd005",
      name: "Procesar una URL por vez",
      type: "n8n-nodes-base.splitInBatches",
      typeVersion: 3,
      position: [-340, 0]
    },
    {
      parameters: {
        url: "={{ $json.source_url }}",
        sendHeaders: true,
        headerParameters: {
          parameters: [
            {
              name: "User-Agent",
              value: "GospelLibraryIA/0.1 n8n-curated-ingestion https://www.estudiopy.com"
            },
            {
              name: "Accept-Language",
              value: "es,es-419;q=0.9"
            }
          ]
        },
        options: {
          timeout: 30000,
          response: {
            response: {
              fullResponse: true,
              neverError: true,
              responseFormat: "text"
            }
          }
        }
      },
      id: "ea653fb0-6854-456d-bd58-8d74015ce006",
      name: "Descargar página o recurso",
      type: "n8n-nodes-base.httpRequest",
      typeVersion: 4.2,
      position: [-100, 0]
    },
    {
      parameters: {
        jsCode: code("02_detectar_tipo_recurso.js")
      },
      id: "fe6618c7-6d45-4d9a-af66-8b753f3c5007",
      name: "Detectar tipo de recurso",
      type: "n8n-nodes-base.code",
      typeVersion: 2,
      position: [140, 0]
    },
    {
      parameters: {
        jsCode: code("03_limpiar_html_extraer_contenido.js")
      },
      id: "56ec6709-d324-46fc-953f-d577fb5db008",
      name: "Limpiar HTML y extraer contenido",
      type: "n8n-nodes-base.code",
      typeVersion: 2,
      position: [380, 0]
    },
    {
      parameters: {
        jsCode: code("04_validar_espanol_calidad.js")
      },
      id: "adca682b-1a28-4d89-996a-2072f5025009",
      name: "Validar español y calidad mínima",
      type: "n8n-nodes-base.code",
      typeVersion: 2,
      position: [620, 0]
    },
    {
      parameters: {
        jsCode: code("05_preparar_payload.js")
      },
      id: "4d6a6a9c-5ef2-4107-a349-bc036358b010",
      name: "Preparar payload para Gospel Library IA",
      type: "n8n-nodes-base.code",
      typeVersion: 2,
      position: [860, 0]
    },
    {
      parameters: {
        conditions: {
          options: {
            caseSensitive: true,
            leftValue: "",
            typeValidation: "strict",
            version: 2
          },
          conditions: [
            {
              id: "94b821e7-85e7-4388-8ed8-3f57f0823011",
              leftValue: "={{ $json.status }}",
              rightValue: "ready",
              operator: {
                type: "string",
                operation: "equals"
              }
            }
          ],
          combinator: "and"
        },
        options: {}
      },
      id: "7c46ea75-9f1a-439c-ae56-c8e649c86012",
      name: "¿Documento válido?",
      type: "n8n-nodes-base.if",
      typeVersion: 2.2,
      position: [1100, 0]
    },
    {
      parameters: {
        method: "POST",
        url: "https://api.estudiopy.com/api/ingestion/documents",
        sendHeaders: true,
        headerParameters: {
          parameters: [
            {
              name: "Content-Type",
              value: "application/json"
            },
            {
              name: "X-Ingestion-Key",
              value: ""
            }
          ]
        },
        sendBody: true,
        contentType: "raw",
        rawContentType: "application/json",
        body: "={{ JSON.stringify($json) }}",
        options: {
          timeout: 30000,
          response: {
            response: {
              fullResponse: true,
              neverError: true,
              responseFormat: "json"
            }
          }
        }
      },
      id: "50627c79-e2fa-47a8-9ef7-f98c17a35013",
      name: "Enviar documento a Gospel Library IA",
      type: "n8n-nodes-base.httpRequest",
      typeVersion: 4.2,
      position: [1340, -120]
    },
    {
      parameters: {
        jsCode: code("06_registrar_resultado_enviado.js")
      },
      id: "7075e1ac-f49c-4a17-a5ee-e2b8c191f014",
      name: "Registrar resultado enviado",
      type: "n8n-nodes-base.code",
      typeVersion: 2,
      position: [1580, -120]
    },
    {
      parameters: {
        jsCode: code("07_registrar_resultado_omitido.js")
      },
      id: "65fd35ff-cf21-4d03-939a-c64384585803",
      name: "Registrar resultado omitido",
      type: "n8n-nodes-base.code",
      typeVersion: 2,
      position: [1340, 120]
    },
    {
      parameters: {
        amount: 3,
        unit: "seconds"
      },
      id: "410f67bc-66b0-4942-8524-2f8070724015",
      name: "Pausa respetuosa",
      type: "n8n-nodes-base.wait",
      typeVersion: 1.1,
      position: [1820, 0],
      webhookId: "ef44b441-d506-46da-9332-1a6f15718016"
    },
    {
      parameters: {
        jsCode: code("08_resumen_lote.js")
      },
      id: "d0fb9cf7-22bd-46bd-9e41-5071b6b020e0",
      name: "Resumen de lote",
      type: "n8n-nodes-base.code",
      typeVersion: 2,
      position: [-100, 260]
    }
  ],
  pinData: {},
  connections: {
    "Inicio manual - Ingesta curada": {
      main: [[{ node: "URLs curadas en español", type: "main", index: 0 }]]
    },
    "URLs curadas en español": {
      main: [[{ node: "Inicializar reporte de lote", type: "main", index: 0 }]]
    },
    "Inicializar reporte de lote": {
      main: [[{ node: "Separar lista de URLs", type: "main", index: 0 }]]
    },
    "Separar lista de URLs": {
      main: [[{ node: "Procesar una URL por vez", type: "main", index: 0 }]]
    },
    "Procesar una URL por vez": {
      main: [
        [{ node: "Descargar página o recurso", type: "main", index: 0 }],
        [{ node: "Resumen de lote", type: "main", index: 0 }]
      ]
    },
    "Descargar página o recurso": {
      main: [[{ node: "Detectar tipo de recurso", type: "main", index: 0 }]]
    },
    "Detectar tipo de recurso": {
      main: [[{ node: "Limpiar HTML y extraer contenido", type: "main", index: 0 }]]
    },
    "Limpiar HTML y extraer contenido": {
      main: [[{ node: "Validar español y calidad mínima", type: "main", index: 0 }]]
    },
    "Validar español y calidad mínima": {
      main: [[{ node: "Preparar payload para Gospel Library IA", type: "main", index: 0 }]]
    },
    "Preparar payload para Gospel Library IA": {
      main: [[{ node: "¿Documento válido?", type: "main", index: 0 }]]
    },
    "¿Documento válido?": {
      main: [
        [{ node: "Enviar documento a Gospel Library IA", type: "main", index: 0 }],
        [{ node: "Registrar resultado omitido", type: "main", index: 0 }]
      ]
    },
    "Enviar documento a Gospel Library IA": {
      main: [[{ node: "Registrar resultado enviado", type: "main", index: 0 }]]
    },
    "Registrar resultado enviado": {
      main: [[{ node: "Pausa respetuosa", type: "main", index: 0 }]]
    },
    "Registrar resultado omitido": {
      main: [[{ node: "Pausa respetuosa", type: "main", index: 0 }]]
    },
    "Pausa respetuosa": {
      main: [[{ node: "Procesar una URL por vez", type: "main", index: 0 }]]
    }
  },
  active: false,
  settings: {
    executionOrder: "v1",
    saveManualExecutions: true
  },
  versionId: "28ee1ab7-eb17-427e-8fb8-5cc22be5a017",
  meta: {
    templateCredsSetupCompleted: false
  },
  tags: []
};

writeFileSync(
  join(root, "gospel_library_curated_ingestion_v1.workflow.json"),
  `${JSON.stringify(workflow, null, 2)}\n`,
  "utf8"
);
