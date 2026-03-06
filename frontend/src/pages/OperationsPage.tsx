export function OperationsPage() {
  return (
    <section className="stack-lg">
      <div className="hero">
        <div>
          <p className="eyebrow">Operacional</p>
          <h2>Eventos retroativos</h2>
          <p className="muted">A API já aceita aportes, resgates e trades retroativos com recálculo completo.</p>
        </div>
      </div>

      <div className="panel stack-md">
        <h3>Fluxo sugerido</h3>
        <ol className="ordered-list">
          <li>Cadastrar cotistas e o fundo.</li>
          <li>Lançar aporte inicial na data de início.</li>
          <li>Lançar trades nas datas históricas desejadas.</li>
          <li>Executar sincronização de histórico, live e proventos.</li>
          <li>Ao incluir evento retroativo, acionar recálculo do fundo.</li>
        </ol>
      </div>

      <div className="panel stack-md">
        <h3>Endpoints disponíveis</h3>
        <ul className="bullets">
          <li>`POST /funds`</li>
          <li>`POST /investors`</li>
          <li>`POST /funds/{'{'}id{'}'}/capital-events`</li>
          <li>`POST /funds/{'{'}id{'}'}/trades`</li>
          <li>`POST /funds/{'{'}id{'}'}/recalculate`</li>
          <li>`POST /pricing/sync/history`</li>
          <li>`POST /pricing/sync/live`</li>
          <li>`POST /pricing/sync/dividends`</li>
        </ul>
      </div>
    </section>
  )
}
