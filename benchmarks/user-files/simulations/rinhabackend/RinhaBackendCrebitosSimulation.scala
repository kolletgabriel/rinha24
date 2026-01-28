import scala.concurrent.duration._

import scala.util.Random

import util.Try

import io.gatling.commons.validation._
import io.gatling.core.session.Session
import io.gatling.core.Predef._
import io.gatling.http.Predef._


class RinhaBackendCrebitosSimulation
  extends Simulation {

  def randomClienteId() = Random.between(1, 5 + 1)
  def randomValorTransacao() = Random.between(1, 10000 + 1)
  def randomDescricao() = Random.alphanumeric.take(10).mkString
  def randomTipoTransacao() = Seq("c", "d", "d")(Random.between(0, 2 + 1)) // not used
  def toInt(s: String): Option[Int] = {
    try {
      Some(s.toInt)
    } catch {
      case e: Exception => None
    }
  }

  val validarConsistenciaSaldoLimite = (valor: Option[String], session: Session) => {
    /*
      Essa função é frágil porque depende que haja uma entrada
      chamada 'limite' com valor conversível para int na session
      e também que seja encadeada com com jmesPath("saldo") para
      que 'valor' seja o primeiro argumento da função validadora
      de 'validate(.., ..)'.
      
      =============================================================
      
      Nota para quem não tem experiência em testes de performance:
        O teste de lógica de saldo/limite extrapola o que é comumente 
        feito em testes de performance apenas por causa da natureza
        da Rinha de Backend. Evite fazer esse tipo de coisa em 
        testes de performance, pois não é uma prática recomendada
        normalmente.
    */ 

    val saldo = valor.flatMap(s => Try(s.toInt).toOption)
    val limite = toInt(session("limite").as[String])

    (saldo, limite) match {
      case (Some(s), Some(l)) if s.toInt < l.toInt * -1 => Failure("Limite ultrapassado!")
      case (Some(s), Some(l)) if s.toInt >= l.toInt * -1 => Success(Option("ok"))
      case _ => Failure("WTF?!")
    }
  }

  val httpProtocol = http
    .baseUrl("http://localhost:9999")
    .userAgentHeader("Agente do Caos - 2024/Q1")

  val debitos = scenario("débitos")
    .exec {s =>
      val descricao = randomDescricao()
      val cliente_id = randomClienteId()
      val valor = randomValorTransacao()
      val payload = s"""{"value": ${valor}, "type": "d", "desc": "${descricao}"}"""
      val session = s.setAll(Map("descricao" -> descricao, "cliente_id" -> cliente_id, "payload" -> payload))
      session
    }
    .exec(
      http("débitos")
      .post(s => s"/customers/${s("cliente_id").as[String]}/transaction")
          .header("content-type", "application/json")
          .body(StringBody(s => s("payload").as[String]))
          .check(
            status.in(200, 422),
            status.saveAs("httpStatus"))
          .checkIf(s => s("httpStatus").as[String] == "200") { jmesPath("overdraft_limit").saveAs("limite") }
          .checkIf(s => s("httpStatus").as[String] == "200") {
            jmesPath("balance").validate("ConsistenciaSaldoLimite - Transação", validarConsistenciaSaldoLimite)
          }
    )

  val creditos = scenario("créditos")
    .exec {s =>
      val descricao = randomDescricao()
      val cliente_id = randomClienteId()
      val valor = randomValorTransacao()
      val payload = s"""{"value": ${valor}, "type": "c", "desc": "${descricao}"}"""
      val session = s.setAll(Map("descricao" -> descricao, "cliente_id" -> cliente_id, "payload" -> payload))
      session
    }
    .exec(
      http("créditos")
      .post(s => s"/customers/${s("cliente_id").as[String]}/transaction")
          .header("content-type", "application/json")
          .body(StringBody(s => s("payload").as[String]))
          .check(
            status.in(200),
            jmesPath("overdraft_limit").saveAs("limite"),
            jmesPath("balance").validate("ConsistenciaSaldoLimite - Transação", validarConsistenciaSaldoLimite)
          )
    )

  val extratos = scenario("extratos")
    .exec(
      http("extratos")
      .get(s => s"/customers/${randomClienteId()}/statement")
      .check(
        jmesPath("balance.overdraft_limit").saveAs("limite"),
        jmesPath("balance.total").validate("ConsistenciaSaldoLimite - Extrato", validarConsistenciaSaldoLimite)
    )
  )

  val validacaConcorrentesNumRequests = 25
  val validacaoTransacoesConcorrentes = (tipo: String) =>
    scenario(s"validação concorrência transações - ${tipo}")
    .exec(
      http("validações")
      .post(s"/customers/1/transaction")
          .header("content-type", "application/json")
          .body(StringBody(s"""{"value": 1, "type": "${tipo}", "desc": "validacao"}"""))
          .check(status.is(200))
    )
  
  val validacaoTransacoesConcorrentesSaldo = (saldoEsperado: Int) =>
    scenario(s"validação concorrência saldo - ${saldoEsperado}")
    .exec(
      http("validações")
      .get(s"/customers/1/statement")
      .check(
        jmesPath("balance.total").ofType[Int].is(saldoEsperado)
      )
    )

  val saldosIniciaisClientes = Array(
    Map("id" -> 1, "limite" ->   1000 * 100),
    Map("id" -> 2, "limite" ->    800 * 100),
    Map("id" -> 3, "limite" ->  10000 * 100),
    Map("id" -> 4, "limite" -> 100000 * 100),
    Map("id" -> 5, "limite" ->   5000 * 100),
  )

  val criterioClienteNaoEcontrado = scenario("validação HTTP 404")
    .exec(
      http("validações")
      .get("/customers/6/statement")
      .check(status.is(404))
    )

  val criteriosClientes = scenario("validações")
    .feed(saldosIniciaisClientes)
    .exec(
      /*
        Os valores de http(...) essão duplicados propositalmente
        para que sejam agrupados no relatório e ocupem menos espaço.
        O lado negativo é que, em caso de falha, pode não ser possível
        saber sua causa exata.
      */ 
      http("validações")
      .get("/customers/#{id}/statement")
      .check(
        status.is(200),
        jmesPath("balance.overdraft_limit").ofType[String].is("#{limite}"),
        jmesPath("balance.total").ofType[String].is("0")
      )
    )
    .exec(
      http("validações")
      .post("/customers/#{id}/transaction")
          .header("content-type", "application/json")
          .body(StringBody(s"""{"value": 1, "type": "c", "desc": "toma"}"""))
          .check(
            status.in(200),
            jmesPath("overdraft_limit").saveAs("limite"),
            jmesPath("balance").validate("ConsistenciaSaldoLimite - Transação", validarConsistenciaSaldoLimite)
          )
    )
    .exec(
      http("validações")
      .post("/customers/#{id}/transaction")
          .header("content-type", "application/json")
          .body(StringBody(s"""{"value": 1, "type": "d", "desc": "devolve"}"""))
          .check(
            status.in(200),
            jmesPath("overdraft_limit").saveAs("limite"),
            jmesPath("balance").validate("ConsistenciaSaldoLimite - Transação", validarConsistenciaSaldoLimite)
          )
    )
    .exec(
      http("validações")
      .get("/customers/#{id}/statement")
      .check(
        jmesPath("recent_transactions[0].desc").ofType[String].is("devolve"),
        jmesPath("recent_transactions[0].type").ofType[String].is("d"),
        jmesPath("recent_transactions[0].value").ofType[Int].is("1"),
        jmesPath("recent_transactions[1].desc").ofType[String].is("toma"),
        jmesPath("recent_transactions[1].type").ofType[String].is("c"),
        jmesPath("recent_transactions[1].value").ofType[Int].is("1")
      )
    )
    .exec( // Consistencia do extrato
      http("validações")
      .post("/customers/#{id}/transaction")
          .header("content-type", "application/json")
          .body(StringBody(s"""{"value": 1, "type": "c", "desc": "danada"}"""))
          .check(
            status.in(200),
            jmesPath("balance").saveAs("saldo"),
            jmesPath("overdraft_limit").saveAs("limite")
          )
          .resources(
            // 5 consultas simultâneas ao extrato para verificar consistência
            http("validações").get("/customers/#{id}/statement").check(
              jmesPath("recent_transactions[0].desc").ofType[String].is("danada"),
              jmesPath("recent_transactions[0].type").ofType[String].is("c"),
              jmesPath("recent_transactions[0].value").ofType[Int].is("1"),
              jmesPath("balance.overdraft_limit").ofType[String].is("#{limite}"),
              jmesPath("balance.total").ofType[String].is("#{saldo}")
            ),
            http("validações").get("/customers/#{id}/statement").check(
              jmesPath("recent_transactions[0].desc").ofType[String].is("danada"),
              jmesPath("recent_transactions[0].type").ofType[String].is("c"),
              jmesPath("recent_transactions[0].value").ofType[Int].is("1"),
              jmesPath("balance.overdraft_limit").ofType[String].is("#{limite}"),
              jmesPath("balance.total").ofType[String].is("#{saldo}")
            ),
            http("validações").get("/customers/#{id}/statement").check(
              jmesPath("recent_transactions[0].desc").ofType[String].is("danada"),
              jmesPath("recent_transactions[0].type").ofType[String].is("c"),
              jmesPath("recent_transactions[0].value").ofType[Int].is("1"),
              jmesPath("balance.overdraft_limit").ofType[String].is("#{limite}"),
              jmesPath("balance.total").ofType[String].is("#{saldo}")
            ),
            http("validações").get("/customers/#{id}/statement").check(
              jmesPath("recent_transactions[0].desc").ofType[String].is("danada"),
              jmesPath("recent_transactions[0].type").ofType[String].is("c"),
              jmesPath("recent_transactions[0].value").ofType[Int].is("1"),
              jmesPath("balance.overdraft_limit").ofType[String].is("#{limite}"),
              jmesPath("balance.total").ofType[String].is("#{saldo}")
            )
        )
    )
  
  .exec(
      http("validações")
      .post("/customers/#{id}/transaction")
          .header("content-type", "application/json")
          .body(StringBody(s"""{"value": 1.2, "type": "d", "desc": "devolve"}"""))
          .check(status.in(422, 400))
    )
    .exec(
      http("validações")
      .post("/customers/#{id}/transaction")
          .header("content-type", "application/json")
          .body(StringBody(s"""{"value": 1, "type": "x", "desc": "devolve"}"""))
          .check(status.in(422, 400))
    )
    .exec(
      http("validações")
      .post("/customers/#{id}/transaction")
          .header("content-type", "application/json")
          .body(StringBody(s"""{"value": 1, "type": "c", "desc": "123456789 e mais um pouco"}"""))
          .check(status.in(422, 400))
    )
    .exec(
      http("validações")
      .post("/customers/#{id}/transaction")
          .header("content-type", "application/json")
          .body(StringBody(s"""{"value": 1, "type": "c", "desc": ""}"""))
          .check(status.in(422, 400))
    )
    .exec(
      http("validações")
      .post("/customers/#{id}/transaction")
          .header("content-type", "application/json")
          .body(StringBody(s"""{"value": 1, "type": "c", "desc": null}"""))
          .check(status.in(422, 400))
    )

  /* 
    Separar créditos e débitos dá uma visão
    melhor sobre como as duas operações se
    comportam individualmente.
  */
  setUp(
    validacaoTransacoesConcorrentes("d").inject(
      atOnceUsers(validacaConcorrentesNumRequests)
    ).andThen(
      validacaoTransacoesConcorrentesSaldo(validacaConcorrentesNumRequests * -1).inject(
        atOnceUsers(1)
      )
    ).andThen(
      validacaoTransacoesConcorrentes("c").inject(
        atOnceUsers(validacaConcorrentesNumRequests)
      ).andThen(
        validacaoTransacoesConcorrentesSaldo(0).inject(
          atOnceUsers(1)
        )
      )
    ).andThen(
      criteriosClientes.inject(
        atOnceUsers(saldosIniciaisClientes.length)
      ),
      criterioClienteNaoEcontrado.inject(
        atOnceUsers(1)
      ).andThen(
        debitos.inject(
          rampUsersPerSec(1).to(220).during(2.minutes),
          constantUsersPerSec(220).during(2.minutes)
        ),
        creditos.inject(
          rampUsersPerSec(1).to(110).during(2.minutes),
          constantUsersPerSec(110).during(2.minutes)
        ),
        extratos.inject(
          rampUsersPerSec(1).to(10).during(2.minutes),
          constantUsersPerSec(10).during(2.minutes)
        )
      )
    )
  ).protocols(httpProtocol)
}
