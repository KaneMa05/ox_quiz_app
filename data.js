/**
 * 임시 데이터 (나중에 DB에서 같은 필드로 내려주면 됩니다)
 * subjects → units → questions
 * question: body(문항), answer(true=O), explanation(해설)
 */
window.OX_CURRICULUM = [
  {
    id: "sub-const",
    name: "헌법",
    units: [
      {
        id: "unit-1",
        name: "총강",
        questions: [
          {
            body: "대한민국은 민주공화국이다.",
            answer: true,
            explanation: "헌법 제1조 제1항.",
          },
          {
            body: "대한민국의 수도는 부산이다.",
            answer: false,
            explanation: "수도는 서울입니다.",
          },
        ],
      },
      {
        id: "unit-2",
        name: "국회",
        questions: [
          {
            body: "국회는 단원제이다.",
            answer: true,
            explanation: "단원제 국회입니다.",
          },
        ],
      },
    ],
  },
  {
    id: "sub-admin",
    name: "행정법",
    units: [
      {
        id: "unit-a1",
        name: "행정법 개론",
        questions: [
          {
            body: "행정법은 공법에 해당한다.",
            answer: true,
            explanation: "대표적인 공법입니다.",
          },
        ],
      },
    ],
  },
];
