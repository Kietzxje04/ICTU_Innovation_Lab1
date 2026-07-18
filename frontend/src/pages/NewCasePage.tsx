import { ArrowLeft, ArrowRight, Check, FileCheck2, Route as RouteIcon, ShieldAlert } from 'lucide-react'
import { useMemo, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { buildRoute, getRouteReasons, NODE_LABELS, PRODUCT_LABELS, type CaseContext, type ProductType } from '../domain'
import { documentOptions } from '../mock-data'
import { useReadiness } from '../readiness-context'

const initialProduct: ProductType = 'WORKING_CAPITAL'

export function NewCasePage() {
  const navigate = useNavigate()
  const { createCase } = useReadiness()
  const [product, setProduct] = useState<ProductType>(initialProduct)
  const [submitted, setSubmitted] = useState<string[]>([...documentOptions[initialProduct]])
  const [amlFlags, setAmlFlags] = useState('')
  const required = [...documentOptions[product]]
  const previewContext = useMemo<CaseContext>(() => ({
    case_id: 'PREVIEW', customer_id: 'PREVIEW', existing_customer: true, product, requested_amount: 1,
    relationship_months: 0, submitted_documents: submitted, required_documents: required, annual_revenue: null,
    pretax_profit_last_2_years: [], tax_declared_revenue: null, cic_bad_debt: false,
    kyc_aml_flags: amlFlags.split(',').map((item) => item.trim()).filter(Boolean), metadata: {},
  }), [amlFlags, product, submitted, required])
  const route = buildRoute(previewContext)

  const changeProduct = (next: ProductType) => {
    setProduct(next)
    setSubmitted([...documentOptions[next]])
  }
  const toggleDocument = (document: string) => setSubmitted((current) => current.includes(document) ? current.filter((item) => item !== document) : [...current, document])

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const caseId = String(data.get('case_id')).trim()
    const companyName = String(data.get('company_name')).trim()
    const context: CaseContext = {
      case_id: caseId,
      customer_id: String(data.get('customer_id')).trim(),
      existing_customer: data.get('existing_customer') === 'on',
      product,
      requested_amount: Number(data.get('requested_amount')),
      relationship_months: Number(data.get('relationship_months')),
      submitted_documents: submitted,
      required_documents: required,
      annual_revenue: Number(data.get('annual_revenue')) || null,
      pretax_profit_last_2_years: [Number(data.get('profit_year_1')) || 0, Number(data.get('profit_year_2')) || 0],
      tax_declared_revenue: Number(data.get('tax_declared_revenue')) || null,
      cic_bad_debt: data.get('cic_bad_debt') === 'on',
      kyc_aml_flags: amlFlags.split(',').map((item) => item.trim()).filter(Boolean),
      metadata: { industry: String(data.get('industry')).trim(), branch: String(data.get('branch')).trim(), currency: 'VND' },
    }
    const next = createCase({ context, company_name: companyName, owner: String(data.get('owner')).trim() })
    navigate(`/cases/${next.id}`)
  }

  return <main className="page intake-page">
    <Link className="back-link" to="/"><ArrowLeft size={15} /> Quay lại dashboard</Link>
    <div className="page-heading"><div><p className="eyebrow">CASE INTAKE</p><h1>Tạo hồ sơ readiness</h1><p>Nhập dữ liệu theo contract CaseContext; workflow dưới đây chỉ mô phỏng ở frontend.</p></div></div>
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
        <section className="form-section"><div className="form-section-title"><span>02</span><div><h2>Sản phẩm và tài chính</h2><p>Route thay đổi theo sản phẩm đã chọn</p></div></div><div className="product-selector">{(['WORKING_CAPITAL', 'CORPORATE_OVERDRAFT'] as ProductType[]).map((item) => <button type="button" key={item} onClick={() => changeProduct(item)} className={product === item ? 'selected' : ''}><FileCheck2 size={18} /><strong>{PRODUCT_LABELS[item]}</strong><span>{item === 'WORKING_CAPITAL' ? 'Tài chính · Thuế · Tín dụng' : 'Vòng quay tài khoản · Tín dụng'}</span></button>)}</div><div className="form-grid">
          <label>Số tiền đề nghị (VND)<input name="requested_amount" type="number" min="1" defaultValue="5000000000" required /></label>
          <label>Doanh thu năm<input name="annual_revenue" type="number" min="0" defaultValue="30000000000" /></label>
          <label>Lợi nhuận trước thuế năm 1<input name="profit_year_1" type="number" defaultValue="1800000000" /></label>
          <label>Lợi nhuận trước thuế năm 2<input name="profit_year_2" type="number" defaultValue="2100000000" /></label>
          <label>Doanh thu khai thuế<input name="tax_declared_revenue" type="number" min="0" defaultValue="29500000000" /></label>
          <label className="check-field danger-check"><input name="cic_bad_debt" type="checkbox" /> Có nợ xấu CIC</label>
        </div></section>
        <section className="form-section"><div className="form-section-title"><span>03</span><div><h2>Tài liệu và AML</h2><p>Document completeness và compliance routing</p></div></div><div className="document-checklist">{required.map((document) => <label key={document}><input type="checkbox" checked={submitted.includes(document)} onChange={() => toggleDocument(document)} /><span><Check size={13} /></span><strong>{document.replaceAll('_', ' ')}</strong></label>)}</div><label className="wide-field">KYC/AML flags (phân cách bằng dấu phẩy)<input value={amlFlags} onChange={(event) => setAmlFlags(event.target.value)} placeholder="Ví dụ: BENEFICIAL_OWNER_REVIEW" /></label></section>
      </div>
      <aside className="route-preview"><div className="route-preview-title"><RouteIcon size={18} /><div><strong>Workflow preview</strong><span>{route.length} nodes · max rework 1</span></div></div><div className="preview-nodes">{route.map((node, index) => <div key={node}><i>{index + 1}</i><span>{NODE_LABELS[node] ?? node}</span>{['MANDATORY_CRITIC', 'CITATION_VALIDATOR', 'POLICY_GATE'].includes(node) && <b>Mandatory</b>}</div>)}</div>{getRouteReasons(previewContext).length > 0 && <div className="route-warning"><ShieldAlert size={15} /><span>{getRouteReasons(previewContext).join(' · ')}</span></div>}<button className="primary-button submit-case" type="submit">Tạo và chạy mock workflow <ArrowRight size={15} /></button><p className="boundary-note">Kết quả chỉ là readiness artifact để cán bộ rà soát, không phải phê duyệt tín dụng.</p></aside>
    </form>
  </main>
}

