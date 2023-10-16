SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for regression
-- ----------------------------
DROP TABLE IF EXISTS `regression`;
CREATE TABLE `RegressionRecord` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `taskId` VARCHAR(255) DEFAULT NULL COMMENT '任务Id',
  `status` varchar(255) DEFAULT NULL COMMENT '执行状态 1-success 2-fail 3-error',
  `type` tinyint(1) DEFAULT NULL COMMENT '项目类型 1-edp 2-rolx 3-rex',
  `createUser` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '创建人',
  `CreateTime` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `log_file` VARCHAR(255) COMMENT 'log文件',
  `excel_file` VARCHAR(255) COMMENT 'excel文件',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=52 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;
