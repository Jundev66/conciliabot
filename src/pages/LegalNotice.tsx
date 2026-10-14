import LegalPage, { LegalSection } from "../components/LegalPage";

export default function LegalNotice() {
  return (
    <LegalPage title="Aviso legal y modelo BYOC" updated="octubre de 2026">
      <LegalSection title="1. Qué es el modelo BYOC">
        <p>
          «BYOC» (<em>bring your own cloud</em>) significa que el software se ejecuta{" "}
          <strong>en el entorno del Cliente</strong>: su equipo, su servidor o su nube. Las facturas
          y los datos del ERP <strong>nunca salen de ahí</strong>. El Proveedor entrega{" "}
          <strong>software</strong>, no un servicio que aloja datos de terceros.
        </p>
      </LegalSection>

      <LegalSection title="2. Qué implica para tus datos">
        <ul className="list-disc space-y-1 pl-5">
          <li>No hay transferencia de Documentos al Proveedor.</li>
          <li>Los modelos pueden correr <strong>localmente</strong> o en la región que elijas.</li>
          <li>El Cliente controla accesos, claves y conservación.</li>
          <li>Se reduce al mínimo la exposición a brechas y a transferencias internacionales.</li>
        </ul>
      </LegalSection>

      <LegalSection title="3. Facturas electrónicas en LATAM">
        <p>
          El software reconoce formatos fiscales por país (por ejemplo, <strong>CFDI</strong> en
          México, <strong>NF-e</strong> en Brasil, <strong>DIAN</strong> en Colombia,{" "}
          <strong>SUNAT</strong> en Perú). El país es <strong>configuración</strong>, no código.
          La verificación se limita a comprobar la validez del documento;{" "}
          <strong>no se altera</strong> el documento original.
        </p>
      </LegalSection>

      <LegalSection title="4. Roles y cumplimiento">
        <p>
          El Cliente es <strong>responsable</strong>; el Proveedor, <strong>encargado</strong>. Los
          datos personales se rigen por la ley aplicable (por ejemplo, <strong>LGPD</strong>,{" "}
          <strong>LFPDPPP</strong>, <strong>Ley 1581</strong>, <strong>Ley 29733</strong>). Los
          detalles se formalizan en el <strong>DPA</strong>.
        </p>
      </LegalSection>

      <LegalSection title="5. Descargos importantes">
        <ul className="list-disc space-y-1 pl-5">
          <li>No es un servicio de <strong>asesoría fiscal, contable o legal</strong>.</li>
          <li>No presenta declaraciones ni pagos ante autoridades.</li>
          <li>Las salidas son <strong>propuestas</strong>; la responsabilidad final es del Usuario.</li>
          <li>El agente no escribe de forma autónoma en el ERP salvo autorización y modo conectado.</li>
        </ul>
      </LegalSection>

      <LegalSection title="6. Sobre esta demostración">
        <p>
          Esta aplicación es una <strong>demo educativa</strong> con datos <strong>sintéticos</strong>.
          No representa a ningún cliente real ni procesa información verdadera. Su fin es mostrar el
          flujo de conciliación con control humano.
        </p>
      </LegalSection>

      <LegalSection title="7. Contacto">
        <p>
          <strong>[correo de contacto]</strong> · <strong>[sitio web]</strong>
        </p>
      </LegalSection>
    </LegalPage>
  );
}
