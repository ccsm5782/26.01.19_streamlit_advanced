import streamlit as st
import datetime
from io import BytesIO
import pandas as pd
import FinanceDataReader as fdr
import plotly.graph_objects as go  # plt 대신 사용할 라이브러리
import os

# 환경 변수 및 헤더 설정
my_name = os.getenv('MY_NAME', '최성민')
st.header(f"📈 {my_name}의 주가 분석 서비스")

@st.cache_data
def get_krx_company_list() -> pd.DataFrame:
    try:
        url = 'http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13'
        # flavor='bs4'와 함께 html5lib가 설치되어 있어야 합니다.
        df_listing = pd.read_html(url, header=0, flavor='bs4', encoding='EUC-KR')[0]
        df_listing = df_listing[['회사명', '종목코드']].copy()
        df_listing['종목코드'] = df_listing['종목코드'].apply(lambda x: f'{x:06}')
        return df_listing
    except Exception as e:
        st.error(f"상장사 명단을 불러오는 데 실패했습니다: {e}")
        return pd.DataFrame(columns=['회사명', '종목코드'])

def get_stock_code_by_company(company_name: str) -> str:
    if company_name.isdigit() and len(company_name) == 6:
        return company_name
    company_df = get_krx_company_list()
    codes = company_df[company_df['회사명'] == company_name]['종목코드'].values
    if len(codes) > 0:
        return codes[0]
    else:
        raise ValueError(f"'{company_name}'을 찾을 수 없습니다.")

# 입력 UI
company_name = st.text_input('회사 이름을 입력해주세요 (예: 삼성전자)')
selected_dates = st.date_input(
    '날짜를 입력해주세요.', 
    (datetime.date(datetime.date.today().year, 1, 1), datetime.date.today()), 
    format="YYYY.MM.DD"
)

confirm_btn = st.button('조회')

if confirm_btn:
    if not company_name:
        st.warning("조회할 회사 이름을 입력하세요.")
    else:
        try:
            with st.spinner('데이터를 수집하는 중...'):
                stock_code = get_stock_code_by_company(company_name)
                start_date = selected_dates[0].strftime("%Y%m%d")
                end_date = selected_dates[1].strftime("%Y%m%d")
                price_df = fdr.DataReader(stock_code, start_date, end_date)
            
            if price_df.empty:
                st.info("해당 기간의 주가 데이터가 없습니다.")
            else:
                st.subheader(f"[{company_name}] 주가 데이터")
                
                # --- Plotly 인터랙티브 차트 (plt 대신 사용) ---
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=price_df.index, 
                    y=price_df['Close'], 
                    mode='lines', 
                    line=dict(color='red', width=2),
                    name='종가'
                ))
                fig.update_layout(
                    title=f"{company_name} 종가 추이",
                    xaxis_title="날짜",
                    yaxis_title="가격 (원)",
                    template="plotly_white",
                    hovermode="x unified"
                )
                st.plotly_chart(fig, use_container_width=True) # 차트 출력

                # 데이터 출력
                st.dataframe(price_df.tail(10), use_container_width=True)

                # 엑셀 다운로드
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    price_df.to_excel(writer, index=True, sheet_name='Sheet1')
                
                st.download_button(
                    label="📥 엑셀 파일 다운로드",
                    data=output.getvalue(),
                    file_name=f"{company_name}_주가.xlsx",
                    mime="application/vnd.ms-excel"
                )
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")