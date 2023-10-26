SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for performance
-- ----------------------------
DROP TABLE IF EXISTS `PerformanceRecord`;
CREATE TABLE `PerformanceRecord` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `taskId` VARCHAR(255) DEFAULT NULL COMMENT '任务Id',
  `status` varchar(20) DEFAULT NULL COMMENT '执行状态 1-success 2-fail 3-error',
  `type` tinyint(1) DEFAULT NULL COMMENT '项目类型 1-edp 2-rolx 3-rex',
  `createUser` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '创建人',
  `execution_time` time AS (TIMEDIFF(end_date, start_date)) STORED COMMENT '执行时长',
  `start_date` datetime COMMENT '执行开始时间',
  `end_date` datetime COMMENT '执行结束时间',
  `createDate` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=52 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;



# 20231023，修改列名
ALTER TABLE `PerformanceRecord`
CHANGE COLUMN createDate createTime datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间';

# 20231026，新增output列,
# 用于储存shell脚本fsx连接情况，通过改字段判断脚本是否执行成功，如果登录登出字段没有在output中，则判定shell脚本执行失败

ALTER TABLE `PerformanceRecord`
ADD COLUMN output VARCHAR(5000) DEFAULT NULL COMMENT '记录shell脚本连接情况';