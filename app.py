import streamlit as st
import datetime
from io import BytesIO
import pandas as pd
import FinanceDataReader as fdr
import plotly.graph_objects as go
from plotly.subplots import make_subplots # 서브플롯 생성을 위한 라이브러리
import os

# 환경 변수 및 헤더 설정
my_name = os.getenv('MY_NAME')
st.header(f"📈 {my_name}의 주가 분석 서비스")

@st.cache_data
def get_krx_company_list() -> pd.DataFrame:
    try:
        url = 'http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13'
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
    if len(codes) > 0: return codes[0]
    else: raise ValueError(f"'{company_name}'을 찾을 수 없습니다.")

company_name = st.text_input('회사 이름을 입력해주세요 (예: 삼성전자)')
selected_dates = st.date_input('날짜를 입력해주세요.', (datetime.date(datetime.date.today().year, 1, 1), datetime.date.today()))

if st.button('조회'):
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
                # --- 2단 차트 구성 (1행: 선 차트, 2행: 캔들 차트) ---
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                   vertical_spacing=0.1, subplot_titles=('종가 추이', '캔들 차트'),
                                   row_heights=[0.4, 0.6])

                # 1. 일반 선 차트 (종가)
                fig.add_trace(go.Scatter(x=price_df.index, y=price_df['Close'], 
                                         name='종가', line=dict(color='blue')), row=1, col=1)

                # 2. 캔들 차트
                fig.add_trace(go.Candlestick(x=price_df.index,
                                             open=price_df['Open'], high=price_df['High'],
                                             low=price_df['Low'], close=price_df['Close'],
                                             name='캔들'), row=2, col=1)

                fig.update_layout(title_text=f"{company_name} 분석 차트",
                                  xaxis2_rangeslider_visible=False, # 캔들차트 하단 슬라이더 숨기기
                                  template="plotly_white", height=800)
                
                st.plotly_chart(fig, use_container_width=True)

                st.dataframe(price_df.tail(10), use_container_width=True)

                # 엑셀 다운로드
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    price_df.to_excel(writer, index=True, sheet_name='Sheet1')
                st.download_button(label="📥 엑셀 다운로드", data=output.getvalue(),
                                   file_name=f"{company_name}_주가.xlsx", mime="application/vnd.ms-excel")
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")