"""Process Manual Dialog — historical evolution & technical explanation for each process."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTabWidget, QTextEdit, QWidget,
)
from PySide6.QtCore import Qt
from core.translations import T


MANUALS = {
    "lacquer_formulation": {
        "title": "Formulación de Laca",
        "tabs": [
            {
                "title": "Visión General",
                "content": """
<h2>Formulación de Laca para Discos de Corte</h2>
<p>La laca para discos fonográficos es un recubrimiento nitrocelulósico
aplicado sobre un sustrato de aluminio (o vidrio en discos tempranos).
La formulación precisa determina la calidad de grabación, la vida útil del
estampador y las características sonoras del disco prensado.</p>

<h3>Componentes Principales</h3>
<ul>
<li><b>Nitrocelulosa (NC):</b> Agente filmógeno principal. Distintas
viscosidades (RS 1/4", RS 1/2", SS) para controlar la dureza y
flexibilidad.</li>
<li><b>Plastificantes:</b> Aceite de ricino, dibutil ftalato (DBP),
diocil ftalato (DOP), poliésteres. Reducen la fragilidad y mejoran
la elasticidad del corte.</li>
<li><b>Solventes:</b> Acetona, MEK, MIBK, tolueno, xileno, etanol.
El balance de evaporación es crítico para evitar velo (blush) y
asegurar un curado uniforme.</li>
<li><b>Resinas modificadoras:</b> Resinas cetónicas (como LA-57), resinas
de formaldehído, aceites alquídicos — mejoran adhesión, dureza superficial
y compatibilidad con el plateado.</li>
<li><b>Aditivos:</b> Estabilizadores UV, antioxidantes, agentes
niveladores, tintes (negro).</li>
</ul>
""",
            },
            {
                "title": "Historia — 1920–1950",
                "content": """
<h2>Era Temprana (1920–1950)</h2>

<h3>1920s — Los Inicios</h3>
<p>Los primeros discos de grabación directa usaban discos de cera
(unsurfaced wax masters). Estos eran frágiles y solo permitían una
reproducción limitada. A finales de los 20, la Western Electric
desarrolló el disco de laca nitrocelulósica ("acetate"), que ofrecía
mejor fidelidad y durabilidad.</p>
<p>Las primeras lacas se formulaban con nitrato de celulosa disuelto
en alcanfor (celuloide), pero rápidamente se migró a nitrocelulosa
con plastificantes más estables.</p>

<h3>1930s — Estabilización</h3>
<p>La Radio Corporation of America (RCA) y la Columbia Broadcasting
System (CBS) estandarizaron las formulaciones. El disco de aluminio
con laca de nitrocelulosa se convirtió en el estándar de la industria
para grabación maestra. Se introdujeron los primeros plastificantes
sintéticos (ftalatos).</p>
<p>Durante la Segunda Guerra Mundial, la escasez de materiales forzó
innovaciones: se usaron sucedáneos del alcanfor y se optimizaron las
fórmulas para minimizar el uso de solventes críticos.</p>

<h3>1940s — Maduración</h3>
<p>Aparecieron los primeros fabricantes especializados: <b>Audio
Devices, Inc.</b> (más tarde Audiodisc) y <b>Transco</b> comenzaron
a producir discos de laca comercialmente. Las formulaciones se
volvieron más consistentes y confiables.</p>
<p>La introducción del LP (Long Play) por Columbia en 1948 exigió
lacas con mejor respuesta en alta frecuencia y menor ruido de
superficie. Esto impulsó el refinamiento de la calidad de la
nitrocelulosa y los procesos de filtrado.</p>
""",
            },
            {
                "title": "Historia — 1950–2000",
                "content": """
<h2>Era Moderna (1950–2000)</h2>

<h3>1950s — Oro de la Lacas</h3>
<p><b>Apollo Records</b> (más tarde Apollo/Transco) entró al mercado
y se convirtió en el proveedor dominante. Sus fórmulas "Apollo" se
convirtieron en el estándar de facto. Mejoras en la calidad de la
nitrocelulosa (menor contenido de nitrógeno residual) redujeron el
ruido de superficie.</p>

<h3>1960s — Corte Estéreo</h3>
<p>La introducción del corte estéreo (Westrex 3D, 1958) exigió lacas
más suaves y flexibles para permitir la modulación vertical sin
distorsión. Se incrementó la proporción de plastificantes y se
ajustaron los solventes para un curado más lento.</p>

<h3>1970s — Optimización</h3>
<p>La crisis del petróleo de 1973 afectó la disponibilidad de
solventes. Se desarrollaron formulaciones de bajo VOC. El corte a
media velocidad (half-speed mastering) permitió mejores cortes en
lacas estándar.</p>

<h3>1980s — Declive y DMM</h3>
<p>El auge del CD (1982) redujo drásticamente la demanda de discos
de laca. Varios fabricantes cerraron. <b>Teldec</b> introdujo el
DMM (Direct Metal Mastering), que evitaba la laca por completo
(cortando directamente sobre cobre). Apollo y Transco se fusionaron.</p>

<h3>1990s — Mínimo</h3>
<p>La producción de discos de laca cayó a mínimos históricos. Solo
Apollo/Transco y unos pocos fabricantes especializados continuaron.
Las formulaciones existentes se mantuvieron sin cambios significativos.</p>
""",
            },
            {
                "title": "Historia — 2000–Presente",
                "content": """
<h2>Renacimiento del Vinilo (2000–Presente)</h2>

<h3>2000s — Resurgimiento</h3>
<p>El interés renovado por el vinilo creó una crisis de oferta de
discos de laca. Apollo/Transco luchó por satisfacer la demanda.
La calidad se volvió inconsistente. Nuevos fabricantes comenzaron a
explorar alternativas.</p>

<h3>2010s — Nuevos Actores</h3>
<p><b>Apollo Master Recording Discs</b> lanzó su fórmula "Low Noir"
(menor contenido de negro de humo) para reducir el ruido de superficie.
<b>MDC (Mastering Discs Company)</b> comenzó a producir discos en
Europa. La fórmula "MDC-1" se posicionó como alternativa a Apollo.</p>
<p><b>Elusive Disc</b> y <b>MFSL</b> (Mobile Fidelity Sound Lab)
comenzaron a usar discos de laca virgen (no reciclados) para mejor
calidad.</p>

<h3>2020s — Desafíos Actuales</h3>
<p>Regulaciones ambientales (REACH, EPA) limitan el uso de solventes
tradicionales como tolueno y MEK. Los fabricantes trabajan en
formulaciones con solventes más ecológicos (bio-solventes,
acetona de origen renovable).</p>
<p>La escasez de discos de laca de alta calidad sigue siendo un
problema crítico para la industria del mastering. Nuevos proyectos
de I+D buscan desarrollar alternativas sintéticas y mejorar la
consistencia de las fórmulas existentes.</p>

<h3>Referencias</h3>
<ul>
<li>Apollo/Transco — Master Recording Discs Specifications</li>
<li>JAES papers on lacquer formulation (1970s–1990s)</li>
<li>Lathe Trolls forum — Formulation knowledge base</li>
</ul>
""",
            },
        ],
    },
    "electroplating": {
        "title": "Galvanoplastia (Plateado/Níquel)",
        "tabs": [
            {
                "title": "Visión General",
                "content": """
<h2>Galvanoplastia para Discos Fonográficos</h2>
<p>El proceso de galvanoplastia convierte el disco maestro de laca
en un estampador metálico resistente para prensado. Implica tres
etapas principales: plateado, electroformado de níquel y separación.</p>

<h3>Etapas del Proceso</h3>
<ul>
<li><b>Plateado (Silver Spray / Chemical Silvering):</b> Se aplica
una capa conductora de plata sobre la superficie de laca mediante
reducción química (nitrato de plata + reductor). Esta capa ultrafina
(0.1–0.3 µm) permite el paso de corriente para el electroformado.</li>
<li><b>Electroformado de Níquel (Nickel Sulfamate Bath):</b> El disco
plateado se sumerge en un baño de sulfamato de níquel y se aplica
corriente continua para depositar níquel (0.2–0.4 mm). El baño de
sulfamato produce depósitos con baja tensión interna.</li>
<li><b>Separación (Stripping):</b> El níquel se separa del disco de
laca, generando un "padre" (negativo). De este se generan "madres"
(positivos) y finalmente "estampadores" (negativos).</li>
</ul>

<h3>Química de los Baños</h3>
<ul>
<li><b>Sulfamato de Níquel (Ni(NH₂SO₃)₂):</b> 300–450 g/L</li>
<li><b>Ácido bórico (H₃BO₃):</b> 30–45 g/L (buffer de pH)</li>
<li><b>Cloruro de níquel (NiCl₂·6H₂O):</b> 5–15 g/L (mejora
conductividad y reduce tensión)</li>
<li><b>pH:</b> 3.5–4.5</li>
<li><b>Temperatura:</b> 40–60 °C</li>
<li><b>Densidad de corriente:</b> 2–10 A/dm²</li>
</ul>
""",
            },
            {
                "title": "Historia — 1930–1970",
                "content": """
<h2>Historia de la Galvanoplastia (1930–1970)</h2>

<h3>1930s — Orígenes</h3>
<p>La galvanoplastia para discos fonográficos se desarrolló poco
después de la introducción de los discos de laca. Los primeros
procesos usaban baños de níquel Watts (sulfato de níquel, cloruro
de níquel, ácido bórico). La plata se aplicaba mediante el
<b>espejo de Tollens</b> (reacción de reducción de nitrato de plata
con formaldehído o glucosa).</p>

<h3>1940s — Industrialización</h3>
<p>Durante la guerra, la demanda de discos (para radiodifusión y
comunicaciones militares) impulsó mejoras en los procesos. Se
desarrollaron baños de níquel más estables y se automatizaron
partes del proceso. Las plantas de prensado comenzaron a incluir
líneas de plateado internas.</p>

<h3>1950s — Sulfamato de Níquel</h3>
<p>La gran innovación fue la introducción del baño de <b>sulfamato
de níquel</b> por la empresa <b>M&T Chemicals</b> (1950s). Este baño
producía depósitos con mucha menor tensión interna que los baños
Watts, lo que permitía obtener estampadores más planos y con menos
deformación. Se convirtió en el estándar de la industria.</p>

<h3>1960s — Automatización</h3>
<p>Se introdujeron sistemas automáticos de transporte de discos
entre baños. El control de temperatura y pH se automatizó. Las
primeras plantas de plateado de alta producción (Toolex Alpha)
comenzaron a operar en Europa y EE.UU.</p>
""",
            },
            {
                "title": "Historia — 1970–Presente",
                "content": """
<h2>Era Moderna (1970–Presente)</h2>

<h3>1970s — Refinamiento</h3>
<p>Mejoras en la filtración y purificación de los baños. Se
introdujeron aditivos antiespumantes y tensoactivos específicos
para reducir defectos. El control de la densidad de corriente
mediante rectificadores de estado sólido mejoró la consistencia
del depósito.</p>

<h3>1980s — Pulse Plating</h3>
<p>Se introdujo el plateado por pulsos (pulse plating), que permite
depósitos más densos y con mejor microdistribución. El uso de
corriente pulsada reduce la porosidad y mejora la dureza del
níquel depositado.</p>

<h3>1990s–2000s — Control Computarizado</h3>
<p>Las líneas de galvanoplastia modernas usan control PLC/computarizado
para monitorear y ajustar en tiempo real: temperatura, pH, densidad
de corriente, composición química. Sistemas de análisis automático
(HPLC, espectroscopía) permiten mantener los baños en condiciones
óptimas.</p>

<h3>2010s–Presente — Desafíos Ambientales</h3>
<p>Regulaciones ambientales más estrictas (RoHS, REACH) limitan el
uso de ciertos aditivos y metales. Se investigan alternativas al
níquel (cobalto, aleaciones Ni-Fe). El reciclaje de baños agotados
es ahora obligatorio en la UE.</p>
<ul>
<li>Baños de Ni-Fe (níquel-hierro) para reducir costos</li>
<li>Procesos de plateado sin cianuros</li>
<li>Reciclaje de plata en el proceso de silvering</li>
</ul>
""",
            },
        ],
    },
    "pressing": {
        "title": "Prensado de Discos",
        "tabs": [
            {
                "title": "Visión General",
                "content": """
<h2>Prensado de Discos de Vinilo</h2>
<p>El prensado transforma el estampador metálico (generado en la
galvanoplastia) en discos de vinilo mediante calor y presión.</p>

<h3>Tipos de Prensas</h3>
<ul>
<li><b>Prensas Automáticas:</b> Alimentan pellets de PVC, funden,
prensan y expulsan automáticamente (Toolex Alpha, SMT, Warmtone).
Ciclo de 20–40 segundos por disco.</li>
<li><b>Prensas Manuales/Semiautomáticas:</b> Operación asistida.
Comunes en plantas pequeñas y prensado de calidad.</li>
</ul>

<h3>Parámetros Críticos</h3>
<ul>
<li><b>Temperatura:</b> 150–190 °C (dependiendo de la fórmula de
PVC). Temperatura demasiado baja → no llena; demasiado alta →
degradación del polímero.</li>
<li><b>Presión:</b> 50–200 bar (cierre). Mayores presiones para
discos de 180g.</li>
<li><b>Tiempo de prensado:</b> 15–30 segundos a temperatura y
presión máximas.</li>
<li><b>Tiempo de enfriamiento:</b> 15–60 segundos. El enfriamiento
debe ser uniforme para evitar deformaciones (warp).</li>
<li><b>Calidad del PVC:</b> El compuesto de vinilo incluye PVC,
plastificantes (ftalatos, ahora restringidos), lubricantes (ácido
esteárico), negro de humo (conductor, colorante), estabilizadores
térmicos (Ca-Zn, Ba-Zn, antes plomo).</li>
</ul>

<h3>Defectos Comunes</h3>
<ul>
<li><b>No llena:</b> Temperatura o presión insuficientes</li>
<li><b>Rebaba excesiva:</b> Exceso de material o presión muy alta</li>
<li><b>Disco pegado:</b> Agente desmoldante insuficiente</li>
<li><b>Deformación (warp):</b> Enfriamiento desigual o humedad</li>
<li><b>Marca de estampador:</b> Estampador desgastado</li>
<li><b>Burbujas:</b> Desgasificado insuficiente o material húmedo</li>
</ul>
""",
            },
            {
                "title": "Historia — 1900–1960",
                "content": """
<h2>Historia del Prensado (1900–1960)</h2>

<h3>1900s–1920s — Shellac 78 RPM</h3>
<p>Los primeros discos se fabricaban con <b>goma laca</b> (shellac),
una resina natural secretada por el insecto <i>Kerria lacca</i>.
La shellac se mezclaba con cargas minerales (pizarra molida,
carbonato de calcio) y lubricantes. El prensado era por compresión
con moldes calentados a vapor. Ciclos lentos (2–5 minutos por
disco).</p>

<h3>1930s — Vinilo Aparece</h3>
<p>RCA Victor introdujo el <b>Vinylite</b> (copolímero de cloruro
de vinilo y acetato de vinilo) para discos de transcripción. El
vinilo ofrecía menor ruido de superficie y mayor durabilidad que
la shellac, pero era más caro.</p>

<h3>1940s — Transición</h3>
<p>Durante la guerra, la shellac era escasa (el insecto productor
es de Asia, rutas comerciales interrumpidas). Esto aceleró la
transición al vinilo. Columbia lanzó el LP (33⅓ RPM) en vinilo en
1948. RCA respondió con el single de 45 RPM en 1949.</p>

<h3>1950s — Automatización</h3>
<p>Primeras prensas automáticas: <b>SMT</b> (Stanley M. Tannenbaum)
y <b>Finebilt</b> comenzaron a producir máquinas que integraban
alimentación de PVC, calentamiento, prensado y expulsión. La
velocidad de producción subió a 100–150 discos/hora por prensa.
Las fórmulas de PVC se estabilizaron con compuestos de plomo
(nocturnamente eficaces, pero tóxicos).</p>
""",
            },
            {
                "title": "Historia — 1960–Presente",
                "content": """
<h2>Historia del Prensado (1960–Presente)</h2>

<h3>1960s — Alta Velocidad</h3>
<p><b>Toolex Alpha</b> (Suecia) lanzó su prensa automática, que
se convirtió en el estándar global. Ciclos de 20 segundos con
calentamiento por radiofrecuencia (RF). Producción de 200–300
discos/hora por prensa. El vinilo de 180g se introdujo como
formato premium.</p>

<h3>1970s — Expansión</h3>
<p>La demanda de vinilo alcanzó su pico histórico. Plantas con
docenas de prensas Toolex Alpha. Se introdujeron sistemas de
enfriamiento por agua en los moldes para ciclos más rápidos.</p>

<h3>1980s–1990s — Declive</h3>
<p>El CD mató el mercado del vinilo. Plantas enteras cerraron.
Miles de prensas fueron desguazadas. Solo unas pocas plantas
especializadas (RTI en EE.UU., Optimal en Alemania, Pallas en
Alemania) sobrevivieron. El conocimiento de prensado se perdió
casi por completo.</p>

<h3>2000s–2010s — Renacimiento</h3>
<p>La demanda resurgió. Faltaban prensas, moldes y personal
calificado. Empresas como <b>Warmtone</b> (China) y <b>Phoenix</b>
comenzaron a fabricar nuevas prensas. Plantas antiguas se
reabrieron. Se redescubrieron y mejoraron las fórmulas de PVC
(eliminando plomo, mejorando la fluidez).</p>

<h3>2020s — Presente</h3>
<p>La capacidad de prensado global sigue siendo insuficiente.
Nuevos fabricantes de prensas (Viryl Technologies, Warmtone).
PVC libre de plomo y ftalatos. Automatización y control de
calidad computarizado. Prensa de 180g como estándar de lujo.</p>
<ul>
<li><b>Nuevos materiales:</b> PVC reciclado, bioplásticos</li>
<li><b>Nuevas tecnologías:</b> Prensado con RFID integrado</li>
<li><b>Sostenibilidad:</b> Reducción de mermas, reciclaje de
rebabas</li>
</ul>
""",
            },
        ],
    },
    "cutting": {
        "title": "Corte de Lacas (Mastering)",
        "tabs": [
            {
                "title": "Visión General",
                "content": """
<h2>Corte de Discos Maestros en Laca</h2>
<p>El corte (mastering) es el proceso de transformar la señal de
audio en surcos físicos sobre un disco de laca mediante una
cabeza cortadora (cutterhead).</p>

<h3>Componentes del Sistema de Corte</h3>
<ul>
<li><b>Torno (Lathe):</b> Plataforma giratoria con movimiento
radial preciso (Neumann VMS-70/80, Scully, Westrex, Lyrec).</li>
<li><b>Cabeza Cortadora (Cutterhead):</b> Transductor que convierte
la señal eléctrica en vibración mecánica del estilete. Ejemplos:
Westrex 3D, Neumann SX-74, Ortofon DSS-212, HAECO.</li>
<li><b>Estilete de Corte (Stylus):</b> Generalmente de zafiro o
diamante, con ángulo de 45° para corte estéreo (45/45).</li>
<li><b>Sistema de Vacío:</b> Aspira la viruta de laca durante el
corte para evitar que interfiera con el estilete.</li>
<li><b>Electrónica de Mastering:</b> Ecualizadores, compresores,
limitadores, generador de código de tiempo.</li>
</ul>

<h3>Parámetros de Corte</h3>
<ul>
<li><b>Ángulo de corte:</b> 45° para estéreo (modulación lateral
= suma, vertical = diferencia).</li>
<li><b>Profundidad de corte:</b> ~50–100 µm</li>
<li><b>Velocidad de surco:</b> Mayor en el exterior (~50 cm/s a
33⅓ RPM) → mejor respuesta en alta frecuencia.</li>
<li><b>Frecuencia de corte:</b> Limitada físicamente por la masa
de la cabeza cortadora y la rigidez de la laca.</li>
<li><b>Nivel de corte:</b> Medido en cm/s de velocidad de surco
(típico 5–15 cm/s, hasta 30 cm/s en cortes calientes).</li>
</ul>
""",
            },
            {
                "title": "Historia — 1920–1960",
                "content": """
<h2>Historia del Corte (1920–1960)</h2>

<h3>1920s — Corte Acústico</h3>
<p>Los primeros cortes se hacían <b>acústicamente</b>: la bocina
captaba el sonido y vibraba un diafragma conectado al estilete.
No había amplificación eléctrica. El rango de frecuencia era
limitado (~150–4000 Hz) y el volumen muy restringido. Los
discos eran de cera o shellac directa.</p>

<h3>1930s — Corte Eléctrico</h3>
<p>Western Electric y RCA desarrollaron las primeras <b>cabezas
cortadoras electromagnéticas</b>. El micrófono y la amplificación
permitían controlar el nivel de corte. La respuesta de frecuencia
se amplió a ~50–8000 Hz. Se introdujo el feedback magnético para
reducir la distorsión.</p>

<h3>1940s — Mejoras</h3>
<p>Desarrollo de cabezas cortadoras con bobina móvil (moving coil)
para mejor respuesta transitoria. Fairchild, Grampian, Westrex
introdujeron diseños mejorados. El disco de laca de aluminio se
convirtió en el estándar.</p>

<h3>1950s — LP y Estéreo</h3>
<p>La introducción del LP (33⅓ RPM) en 1948 exigió cortes de mayor
duración con surcos más finos. En 1958, <b>Westrex</b> introdujo
la primera cabeza cortadora estéreo comercial (Westrex 3D), que
modulaba en dos canales a 45° (sistema 45/45 que sigue siendo el
estándar hoy).</p>
""",
            },
            {
                "title": "Historia — 1960–Presente",
                "content": """
<h2>Historia del Corte (1960–Presente)</h2>

<h3>1960s — Transistores y Neumann</h3>
<p><b>Neumann</b> (Alemania) lanzó su torno VMS-70 con la cabeza
SX-68 (y luego SX-74), que se convirtió en el estándar de la
industria. La electrónica transistorizada permitió mayor
potencia y menor distorsión. El sistema de vacío integrado
mejoró la calidad del corte.</p>

<h3>1970s — Half-Speed y DMM</h3>
<p>El corte a media velocidad (<b>half-speed mastering</b>),
popularizado por Stan Ricker y Nautilus Records, mejoraba la
respuesta en alta frecuencia. Teldec introdujo el <b>DMM</b>
(Direct Metal Mastering, 1978) — cortando directamente sobre
cobre, sin laca. Mejor respuesta transitoria pero menor
uniformidad de calidad.</p>

<h3>1980s — Digital</h3>
<p>El mastering digital (SONY PCM-1600, etc.) permitió procesar
la señal digitalmente antes del corte. Los primeros cortes
digitales (CBS, 1980s). El CD redujo la demanda, pero el corte
digital permitió masters más consistentes.</p>

<h3>1990s–2000s — Declive y Resurgimiento</h3>
<p>La producción de tornos de corte cesó (Neumann VMS-80 fue el
último). El conocimiento de mantenimiento y calibración se perdió.
Con el renacimiento del vinilo, surgieron nuevos sistemas:
<b>Elastic Stage</b> (masterización digital con control de
profundidad en tiempo real), <b>Simulathe</b> (emulación digital
del torno), <b>Vinyl Recorder</b> (torno de escritorio).</p>

<h3>2010s–Presente — Innovación</h3>
<p>Cabezas modernas: <b>HAECO</b> (reconstrucción de Westrex 3D
con materiales modernos), <b>Ortofon DSS-212</b>, <b>CARver</b>.
Sistemas de corte semiautomáticos con control de computadora.
Mejora en la calidad del estilete (diamante sintético, geometrías
optimizadas).</p>
<ul>
<li><b>Elastic Stage:</b> Corte con control digital de profundidad</li>
<li><b>Simulathe:</b> Simulación digital de lathe para pre-optimización</li>
<li><b>Tiny Vinyl:</b> Discos de 4–7" para ediciones limitadas</li>
<li><b>Lacquer alternativos:</b> Discos de policarbonato, DMM mejorado</li>
</ul>
""",
            },
        ],
    },
}


class ProcessManualDialog(QDialog):
    """Dialog showing the historical & technical manual for a given process."""

    def __init__(self, process_key: str, parent=None):
        super().__init__(parent)
        manual = MANUALS.get(process_key)
        if manual is None:
            self.setWindowTitle(T("Manual de Proceso"))
            self.setMinimumSize(600, 400)
            layout = QVBoxLayout(self)
            layout.addWidget(QLabel(T("Manual no disponible para este proceso.")))
            close_btn = QPushButton(T("Cerrar"))
            close_btn.clicked.connect(self.accept)
            layout.addWidget(close_btn)
            return

        self.setWindowTitle(T(f"📖 Manual: {manual['title']}"))
        self.setMinimumSize(750, 550)
        self.resize(850, 650)

        layout = QVBoxLayout(self)

        title_label = QLabel(f"<h1>{manual['title']}</h1>")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        tabs = QTabWidget()

        for tab_data in manual["tabs"]:
            tab_widget = QWidget()
            tab_layout = QVBoxLayout(tab_widget)
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setHtml(tab_data["content"])
            tab_layout.addWidget(text_edit)
            tabs.addTab(tab_widget, tab_data["title"])

        layout.addWidget(tabs, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton(T("Cerrar"))
        close_btn.setMinimumWidth(120)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
