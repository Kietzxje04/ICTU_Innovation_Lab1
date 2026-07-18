import { ArrowLeft, ArrowRight, Check, FileCheck2, Route as RouteIcon, ShieldAlert } from 'lucide-react'
import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { readinessApi } from '../api'
import { NODE_LABELS, PRODUCT_LABELS, type CaseContext, type ProductType } from '../domain'
import { useReadiness } from '../readiness-context'

const initialProduct: ProductType = 'WORKING_CAPITAL'

function nullableNumber(data: FormData, name: string) {
  const value = String(data.get(name) ?? '').trim()
  return value === '' ? null : Number(value)
}

function csv(value: string) {
  return value.split(',').map((item) => item.trim()).filter(Boolean)
}

export function NewCasePage() {
  const navigate = useNavigate()
  const { createCase } = useReadiness()
  const [product, setProduct] = useState<ProductType>(initialProduct)
  const [required, setRequired] = useState<string[]>([])
  const [submitted, setSubmitted] = useState<string[]>([])
  const [amlFlags, setAmlFlags] = useState('')
  const [route, setRoute] = useState<string[]>([])
  const [routeReasons, setRouteReasons] = useState<string[]>([])
  const [schemaError, setSchemaError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    setRequired([])
    setSubmitted([])
    setSchemaError('')
    readinessApi.productSchema(product, controller.signal)
      .then((schema) => setRequired(schema.required_documents))
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return
        setSchemaError(reason instanceof Error ? reason.message : 'Không tải được cấu hình sản phẩm từ Agent')
      })
    return () => controller.abort()
  }, [product])

  const previewContext = useMemo<CaseContext>(() => ({
    case_id: 'PREVIEW', customer_id: 'PREVIEW', existing_customer: true, product, requested_amount: 1,
    relationship_months: 24, submitted_documents: submitted, required_documents: required,
    annual_revenue: null, pretax_profit_last_2_years: [], tax_declared_revenue: null,
    collateral_ratio: product === 'WORKING_CAPITAL' ? 0.2 : null,
    account_history_months: product === 'CORPORATE_OVERDRAFT' ? 24 : null,
    twelve_month_credit_turnover: product === 'CORPORATE_OVERDRAFT' ? 12 : null,
    average_monthly_credit_inflow: product === 'CORPORATE_OVERDRAFT' ? 1 : null,
    turnover_stability_ratio: product === 'CORPORATE_OVERDRAFT' ? 0.8 : null,
    overdraft_purpose: product === 'CORPORATE_OVERDRAFT' ? 'Bổ sung vốn lưu động qua tài khoản thanh toán' : null,
    loan_purpose: product === 'WORKING_CAPITAL' ? 'Bổ sung vốn lưu động' : null,
    account_conduct_flags: [], cic_bad_debt: false, kyc_aml_flags: csv(amlFlags), metadata: {},
  }), [amlFlags, product, required, submitted])

  useEffect(() => {
    if (!required.length) return
    const controller = new AbortController()
    readinessApi.previewRoute(previewContext, controller.signal)
      .then((preview) => {
        setRoute(preview.route)
        setRouteReasons(preview.reasons)
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return
        setSchemaError(reason instanceof Error ? reason.message : 'Không xem trước được workflow Agent')
      })
    return () => controller.abort()
  }, [previewContext, required.length])

  const toggleDocument = (document: string) => setSubmitted((current) =>
    current.includes(document) ? current.filter((item) => item !== document) : [...current, document])

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const caseId = String(data.get('case_id')).trim()
    const companyName = String(data.get('company_name')).trim()
    const relationshipMonths = Number(data.get('relationship_months'))
    const loanPurpose = String(data.get('loan_purpose') ?? '').trim() || null
    const overdraftPurpose = String(data.get('overdraft_purpose') ?? '').trim() || null
    const context: CaseContext = {
      case_id: caseId,
      customer_id: String(data.get('customer_id')).trim(),
      existing_customer: data.get('existing_customer') === 'on',
      product,
      requested_amount: Number(data.get('requested_amount')),
      relationship_months: relationshipMonths,
      submitted_documents: submitted,
      required_documents: required,
      annual_revenue: nullableNumber(data, 'annual_revenue'),
      pretax_profit_last_2_years: [Number(data.get('profit_year_1')) || 0, Number(data.get('profit_year_2')) || 0],
      tax_declared_revenue: nullableNumber(data, 'tax_declared_revenue'),
      collateral_ratio: nullableNumber(data, 'collateral_ratio'),
      account_history_months: nullableNumber(data, 'account_history_months') ?? relationshipMonths,
      twelve_month_credit_turnover: nullableNumber(data, 'twelve_month_credit_turnover'),
      average_monthly_credit_inflow: nullableNumber(data, 'average_monthly_credit_inflow'),
      turnover_stability_ratio: nullableNumber(data, 'turnover_stability_ratio'),
      expected_utilization_ratio: nullableNumber(data, 'expected_utilization_ratio'),
      negative_balance_days: nullableNumber(data, 'negative_balance_days'),
      cleanup_days: nullableNumber(data, 'cleanup_days'),
      overdraft_purpose: overdraftPurpose,
      loan_purpose: loanPurpose,
      account_conduct_flags: csv(String(data.get('account_conduct_flags') ?? '')),
      cic_bad_debt: data.get('cic_bad_debt') === 'on',
      kyc_aml_flags: csv(amlFlags),
      metadata: {
        industry: String(data.get('industry')).trim(),
        branch: String(data.get('branch')).trim(),
        currency: 'VND',
        ...(loanPurpose ? { loan_purpose: loanPurpose } : {}),
        ...(overdraftPurpose ? { overdraft_purpose: overdraftPurpose } : {}),
      },
    }
    setSubmitting(true)
    setSubmitError('')
    try {
      const next = await createCase({ context, company_name: companyName, owner: String(data.get('owner')).trim() })
      navigate(`/cases/${next.id}`)
    } catch (reason) {
      setSubmitError(reason instanceof Error ? reason.message : 'Không thể tạo hồ sơ')
    } finally {
      setSubmitting(false)
    }
  }

  return <main className="page intake-page">
    <Link className="back-link" to="/"><ArrowLeft size={15} /> Quay lại bảng điều hành</Link>
    <div className="page-heading"><div><p className="eyebrow">TIẾP NHẬN HỒ SƠ</p><h1>Tạo hồ sơ đánh giá mức độ sẵn sàng</h1><p>Hệ thống cung cấp ma trận hồ sơ, quy trình và tiêu chí đánh giá; kết quả không phải quyết định phê duyệt tín dụng.</p></div></div>
    <form onSubmit={submit} className="intake-layout">
      <div className="intake-main">
        <section className="form-section"><div className="form-section-title"><span>01</span><div><h2>Định danh hồ sơ</h2><p>Thông tin quản lý và quan hệ khách hàng</p></div></div><div className="form-grid">
          <label>Mã hồ sơ<input name="case_id" defaultValue={`CASE-${Date.now().toString().slice(-6)}`} required /></label>
          <label>Mã khách hàng<input name="customer_id" defaultValue="CUS-" required /></label>
          <label className="span-2">Tên doanh nghiệp<input name="company_name" placeholder="Công ty TNHH..." required /></label>
          <label>Người phụ trách<input name="owner" placeholder="Cán bộ quan hệ khách hàng" required /></label>
          <label>Số tháng quan hệ<input name="relationship_months" type="number" min="0" defaultValue="24" required /></label>
          <label>Ngành nghề<input name="industry" placeholder="Sản xuất, thương mại..." required /></label>
          <label>Chi nhánh<input name="branch" defaultValue="ICTU Thái Nguyên" required /></label>
          <label className="check-field"><input name="existing_customer" type="checkbox" defaultChecked /> Khách hàng hiện hữu</label>
        </div></section>

        <section className="form-section"><div className="form-section-title"><span>02</span><div><h2>Sản phẩm và tài chính</h2><p>Thông tin chung cho đánh giá readiness</p></div></div>
          <div className="product-selector">{(['WORKING_CAPITAL', 'CORPORATE_OVERDRAFT'] as ProductType[]).map((item) => <button type="button" key={item} onClick={() => setProduct(item)} className={product === item ? 'selected' : ''}><FileCheck2 size={18} /><strong>{PRODUCT_LABELS[item]}</strong><span>{item === 'WORKING_CAPITAL' ? 'Mục đích · Tài chính · Thuế' : 'Hạn mức quay vòng · Dòng tiền tài khoản'}</span></button>)}</div>
          <div className="form-grid">
            <label>Số tiền đề nghị (VND)<input name="requested_amount" type="number" min="1" defaultValue="5000000000" required /></label>
            <label>Doanh thu năm<input name="annual_revenue" type="number" min="0" defaultValue="30000000000" /></label>
            <label>Lợi nhuận trước thuế năm 1<input name="profit_year_1" type="number" defaultValue="1800000000" /></label>
            <label>Lợi nhuận trước thuế năm 2<input name="profit_year_2" type="number" defaultValue="2100000000" /></label>
            <label>Doanh thu khai thuế<input name="tax_declared_revenue" type="number" min="0" defaultValue="29500000000" /></label>
            <label className="check-field danger-check"><input name="cic_bad_debt" type="checkbox" /> Có nợ xấu CIC</label>
          </div>
        </section>

        {product === 'CORPORATE_OVERDRAFT' ? <section className="form-section"><div className="form-section-title"><span>03</span><div><h2>Dữ liệu thấu chi doanh nghiệp</h2><p>Đánh giá khả năng vận hành hạn mức quay vòng trên tài khoản thanh toán</p></div></div><div className="form-grid">
          <label className="span-2">Mục đích thấu chi<input name="overdraft_purpose" defaultValue="Bổ sung vốn lưu động qua tài khoản thanh toán" required /></label>
          <label>Lịch sử tài khoản (tháng)<input name="account_history_months" type="number" min="0" defaultValue="24" required /></label>
          <label>Doanh số ghi Có 12 tháng<input name="twelve_month_credit_turnover" type="number" min="0" defaultValue="60000000000" required /></label>
          <label>Dòng tiền ghi Có bình quân tháng<input name="average_monthly_credit_inflow" type="number" min="0" defaultValue="5000000000" /></label>
          <label>Độ ổn định dòng tiền (0-1)<input name="turnover_stability_ratio" type="number" min="0" step="0.01" defaultValue="0.8" required /></label>
          <label>Tỷ lệ sử dụng dự kiến (0-1)<input name="expected_utilization_ratio" type="number" min="0" max="1" step="0.01" defaultValue="0.7" /></label>
          <label>Số ngày dư nợ âm dự kiến<input name="negative_balance_days" type="number" min="0" defaultValue="20" /></label>
          <label>Số ngày hoàn trả dư nợ<input name="cleanup_days" type="number" min="0" defaultValue="7" /></label>
          <label className="span-2">Cờ hành vi tài khoản (phân cách dấu phẩy)<input name="account_conduct_flags" placeholder="Ví dụ: RETURNED_PAYMENT, IRREGULAR_CLEANUP" /></label>
        </div></section> : <section className="form-section"><div className="form-section-title"><span>03</span><div><h2>Dữ liệu vốn lưu động</h2><p>Mục đích sử dụng vốn và thông tin bảo đảm</p></div></div><div className="form-grid">
          <label className="span-2">Mục đích vay<input name="loan_purpose" defaultValue="Bổ sung vốn lưu động phục vụ hoạt động kinh doanh" required /></label>
          <label>Tỷ lệ tài sản bảo đảm (0-1)<input name="collateral_ratio" type="number" min="0" step="0.01" defaultValue="0.3" required /></label>
        </div></section>}

        <section className="form-section"><div className="form-section-title"><span>04</span><div><h2>Tài liệu và phòng chống rửa tiền</h2><p>Ma trận hồ sơ được tải từ hệ thống; mặc định chưa đánh dấu tài liệu đã nộp</p></div></div>
          <div className="document-checklist">{required.map((document) => <label key={document}><input type="checkbox" checked={submitted.includes(document)} onChange={() => toggleDocument(document)} /><span><Check size={13} /></span><strong>{document.replaceAll('_', ' ')}</strong></label>)}</div>
          {!required.length && <p>Đang tải ma trận hồ sơ từ hệ thống...</p>}
          <label className="wide-field">Cảnh báo định danh/phòng chống rửa tiền (phân cách bằng dấu phẩy)<input value={amlFlags} onChange={(event) => setAmlFlags(event.target.value)} placeholder="Ví dụ: cần xác minh chủ sở hữu hưởng lợi" /></label>
        </section>
      </div>

      <aside className="route-preview"><div className="route-preview-title"><RouteIcon size={18} /><div><strong>Xem trước quy trình xử lý</strong><span>{route.length} khâu · làm lại tối đa 1 lần</span></div></div>
        <div className="preview-nodes">{route.map((node, index) => <div key={node}><i>{index + 1}</i><span>{NODE_LABELS[node] ?? node}</span>{['MANDATORY_CRITIC', 'CITATION_VALIDATOR', 'READINESS_RULE_ENGINE', 'POLICY_GATE'].includes(node) && <b>Bắt buộc</b>}</div>)}</div>
        {routeReasons.length > 0 && <div className="route-warning"><ShieldAlert size={15} /><span>{routeReasons.join(' · ')}</span></div>}
        {(schemaError || submitError) && <div className="route-warning"><ShieldAlert size={15} /><span>{schemaError || submitError}</span></div>}
        <button disabled={submitting || !required.length} className="primary-button submit-case" type="submit">{submitting ? 'Đang chạy quy trình tác nhân...' : 'Tạo và chạy quy trình tác nhân'} <ArrowRight size={15} /></button>
        <p className="boundary-note">Các ngưỡng hiện tại là chính sách demo tổng hợp, không phải chính sách chính thức và không tạo hạn mức/lãi suất/phê duyệt tự động.</p>
      </aside>
    </form>
  </main>
}
