import LegalPage, { LegalSection } from "../components/LegalPage";

export default function Terms() {
  return (
    <LegalPage title="Términos y Condiciones" updated="octubre de 2026">
      <LegalSection title="1. Identificación del prestador">
        <p>
          Este software es provisto por <strong>[Razón social del proveedor]</strong>, con domicilio
          en <strong>[domicilio]</strong> y contacto <strong>[correo de contacto]</strong> (en
          adelante, «el Proveedor»). Esta versión es una <strong>demostración</strong> con datos
          sintéticos.
        </p>
      </LegalSection>

      <LegalSection title="2. Objeto y aceptación">
        <p>
          El Proveedor ofrece un software de <strong>conciliación y preparación de registro de
          facturas</strong> asistido por inteligencia artificial. Al instalar o usar el software, el
          Cliente y sus Usuarios aceptan estos Términos. Si no están de acuerdo, no deben usar el
          software.
        </p>
      </LegalSection>

      <LegalSection title="3. Definiciones">
        <p>
          «<strong>Cliente</strong>»: la persona jurídica que licencia el software. «<strong>Usuario
          </strong>»: quien opera el software por cuenta del Cliente. «<strong>Documento</strong>»:
          facturas, comprobantes y datos fiscales. «<strong>ERP</strong>»: sistema de gestión del
          Cliente.
        </p>
      </LegalSection>

      <LegalSection title="4. Licencia de uso">
        <p>
          El Proveedor concede al Cliente una licencia <strong>no exclusiva, no transferible y
          limitada</strong> para instalar y usar el software en su propia infraestructura o equipo,
          durante la vigencia del contrato. El software es <strong>software, no un servicio de
          custodia de datos</strong>: se instala en el entorno del Cliente (modelo BYOC).
        </p>
      </LegalSection>

      <LegalSection title="5. Modelo de despliegue y responsabilidad sobre los datos">
        <p>
          El software corre <strong>dentro del entorno del Cliente</strong>. Los Documentos y los
          datos del ERP <strong>permanecen bajo control del Cliente</strong>. El Cliente es el
          único <strong>responsable del tratamiento</strong> de los datos; el Proveedor actúa, en su
          caso, como <strong>encargado</strong> conforme al contrato de tratamiento de datos (DPA)
          aplicable.
        </p>
      </LegalSection>

      <LegalSection title="6. Obligaciones del Cliente">
        <ul className="list-disc space-y-1 pl-5">
          <li>Contar con base legal y autorizaciones para tratar los Documentos.</li>
          <li>Autorizar expresamente la conexión al ERP antes de cualquier acceso.</li>
          <li>Revisar y aprobar los registros propuestos (HITL) antes de su registro definitivo.</li>
          <li>Mantener la seguridad de su entorno, credenciales y accesos.</li>
        </ul>
      </LegalSection>

      <LegalSection title="7. Naturaleza del servicio y límites">
        <p>
          El software <strong>no presta asesoría fiscal, contable ni legal</strong> y{" "}
          <strong>no presenta declaraciones</strong> ante ninguna autoridad. Sugiere registros y
          señala posibles diferencias; la decisión y el uso final son del Cliente y sus Usuarios.
        </p>
      </LegalSection>

      <LegalSection title="8. Decisiones automatizadas y control humano">
        <p>
          Toda acción con efecto fiscal o económico requiere <strong>aprobación humana</strong>. El
          software no ejecuta pagos, envíos ni borrados de forma autónoma. Las salidas se
          proporcionan como <strong>propuestas</strong> sujetas a validación del Usuario.
        </p>
      </LegalSection>

      <LegalSection title="9. Propiedad intelectual">
        <p>
          El software, su código y su documentación son propiedad del Proveedor o sus licenciantes.
          Los Documentos y datos del Cliente siguen siendo del Cliente. No se adquiere ningún
          derecho sobre ellos.
        </p>
      </LegalSection>

      <LegalSection title="10. Limitación de responsabilidad">
        <p>
          En la máxima medida permitida por la ley, el Proveedor <strong>no será responsable</strong>{" "}
          de daños indirectos, lucro cesante, multas o sanciones derivadas de registros incorrectos,
          decisiones del Usuario o uso indebido del software. La responsabilidad total del Proveedor
          se limita al monto pagado por el Cliente en los <strong>[12]</strong> meses anteriores.
        </p>
      </LegalSection>

      <LegalSection title="11. Garantías">
        <p>
          La versión de <strong>demostración</strong> se entrega «<strong>tal cual</strong>» («AS
          IS»), sin garantías de ningún tipo. Las condiciones de soporte y niveles de servicio se
          rigen por el contrato aplicable.
        </p>
      </LegalSection>

      <LegalSection title="12. Protección de datos">
        <p>
          El tratamiento de datos se rige por la <strong>Política de Privacidad</strong> y el{" "}
          <strong>contrato de tratamiento de datos (DPA)</strong> entre las partes, incluyendo la
          lista de subencargados (por ejemplo, proveedores de modelos) y las reglas de residencia.
        </p>
      </LegalSection>

      <LegalSection title="13. Terminación y ley aplicable">
        <p>
          Cualquiera de las partes puede terminar el contrato conforme a sus términos. Estas
          condiciones se rigen por las leyes de <strong>[país]</strong>, con jurisdicción en{" "}
          <strong>[ciudad, país]</strong>, sin perjuicio de normas imperativas de protección al
          consumidor o de datos que resulten aplicables.
        </p>
      </LegalSection>

      <LegalSection title="14. Contacto">
        <p>
          Consultas sobre estos Términos: <strong>[correo de contacto]</strong>.
        </p>
      </LegalSection>
    </LegalPage>
  );
}
